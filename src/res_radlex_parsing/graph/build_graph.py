"""Build the RadLex knowledge graph from parsed OWL data and persist it to DuckDB.

Consumes the triples/records produced by :mod:`res_radlex_parsing.owl_ingest.parse`,
assembles them into an in-memory ``networkx.DiGraph`` (nodes = RadLex classes keyed by
RID, edges = ``is_a`` plus restriction-derived relations such as ``Part_Of`` and
``Has_Part``), and writes the resulting nodes/edges out to the on-disk DuckDB store via
:mod:`res_radlex_parsing._shared.db` so the graph is inspectable and queryable outside
of Python.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import networkx as nx
import pyarrow as pa

from res_radlex_parsing._shared import db

logger = logging.getLogger(__name__)


class RadLexGraphBuilder:
    """Builds the RadLex knowledge graph from the flattened triples table and persists
    it to DuckDB.

    Loads the ``TripleRow``-shaped Parquet output of
    :class:`res_radlex_parsing.owl_ingest.parse.RadLexOwlParser`, derives node and edge
    tables via SQL — filtering ``type = Class`` subjects into nodes, pivoting literal
    rows (label/synonym/definition) into node attributes, taking direct resource-valued
    triples as edges, and resolving ``owl:Restriction`` blank-node blocks into typed
    edges via a self-join — assembles an in-memory ``networkx.DiGraph``, and writes the
    resulting nodes/edges tables to an on-disk DuckDB database via
    :mod:`res_radlex_parsing._shared.db`.

    Methods are designed for chaining, e.g.::

        RadLexGraphBuilder(triples_path, db_path).load().build().save()

    Attributes:
        triples_path: Filesystem path to the Parquet triples table produced by
            :class:`RadLexOwlParser`.
        db_path: Filesystem path to the destination DuckDB database file.
    """

    def __init__(self, triples_path: Path, db_path: Path) -> None:
        """Initializes the builder without reading or connecting to anything.

        Args:
            triples_path: Filesystem path to the Parquet triples table produced by
                :class:`RadLexOwlParser`.
            db_path: Filesystem path to the destination DuckDB database file.
        """

        self.triples_path = triples_path
        self.db_path = db_path
        self._con: duckdb.DuckDBPyConnection | None = None
        self._graph: nx.DiGraph | None = None
        self._nodes: pa.Table | None = None
        self._edges: pa.Table | None = None

    def load(self) -> RadLexGraphBuilder:
        """Opens a DuckDB connection and registers the triples Parquet file.

        Must be called before :meth:`build`.

        Returns:
            This builder instance, to support method chaining.

        Raises:
            OSError: If ``triples_path`` cannot be read.
        """
        if not self.triples_path.exists():
            raise OSError(f"Triples file not found: {self.triples_path}")

        self._con = db.connect(self.db_path)
        db.create_schema(self._con)
        return self

    def build(self) -> RadLexGraphBuilder:
        """Derives node/edge tables via SQL and assembles the in-memory graph.

        Returns:
            This builder instance, to support method chaining.

        Raises:
            RuntimeError: If called before :meth:`load`.
        """
        self._nodes = self._query_nodes()
        self._edges = self._query_edges()
        self._graph = self._to_networkx(self._nodes, self._edges)

        return self

    def save(self) -> RadLexGraphBuilder:
        """Writes the derived nodes and edges tables to the on-disk DuckDB database.

        Returns:
            This builder instance, to support method chaining.

        Raises:
            RuntimeError: If called before :meth:`build`.
            OSError: If ``db_path`` cannot be written.
        """
        if self._con is None or self._nodes is None or self._edges is None:
            raise RuntimeError("build() must be called before save()")

        db.write_nodes(self._con, self._nodes)
        db.write_edges(self._con, self._edges)

        return self

    def _query_nodes(self) -> pa.Table:
        """Derives the nodes table from the registered triples.

        Returns:
            A table with columns ``rid``, ``label``, ``synonyms`` (list),
            ``definition``, ``is_obsolete``, ``replaced_by_rid`` — one row per
            subject with a ``type = Class`` triple.
        """
        assert self._con is not None

        return self._con.execute(
            """
            WITH triples AS (
                SELECT * FROM read_parquet(?)
            ),
            class_rids AS (
                SELECT DISTINCT subject AS rid
                FROM triples
                WHERE predicate = 'type' AND object = 'Class'
            ),
            labels AS (
                SELECT subject AS rid, any_value(object) AS label
                FROM triples
                WHERE predicate = 'label' AND NOT is_resource AND lang = 'en'
                GROUP BY subject
            ),
            synonyms AS (
                SELECT subject AS rid, list(object) AS synonyms
                FROM triples
                WHERE predicate = 'Synonym' AND NOT is_resource
                GROUP BY subject
            ),
            definitions AS (
                SELECT subject AS rid, any_value(object) AS definition
                FROM triples
                WHERE predicate = 'Definition' AND NOT is_resource
                GROUP BY subject
            ),
            replaced_by AS (
                SELECT subject AS rid, any_value(object) AS replaced_by_rid
                FROM triples
                WHERE predicate = 'Replaced_by'
                GROUP BY subject
            ),
            obsolete_flags AS (
                SELECT DISTINCT subject AS rid
                FROM triples
                WHERE predicate IN ('Replaced_by', 'Preferred_Name_for_Obsolete')
            )
            SELECT
                class_rids.rid,
                labels.label,
                COALESCE(synonyms.synonyms, []::VARCHAR[]) AS synonyms,
                definitions.definition,
                obsolete_flags.rid IS NOT NULL AS is_obsolete,
                replaced_by.replaced_by_rid
            FROM class_rids
            LEFT JOIN labels ON labels.rid = class_rids.rid
            LEFT JOIN synonyms ON synonyms.rid = class_rids.rid
            LEFT JOIN definitions ON definitions.rid = class_rids.rid
            LEFT JOIN obsolete_flags ON obsolete_flags.rid = class_rids.rid
            LEFT JOIN replaced_by ON replaced_by.rid = class_rids.rid
            """,
            [str(self.triples_path)],
        ).fetch_arrow_table()

    def _query_edges(self) -> pa.Table:
        """Derives the edges table from the registered triples.

        Combines direct resource-valued triples (e.g. ``subClassOf`` pointing at a
        real RID) with restriction-derived edges resolved via a self-join over
        ``subClassOf`` -> blank node -> (``onProperty``, ``someValuesFrom``) triples
        sharing the same blank node id.

        Returns:
            A table with columns ``source_rid``, ``target_rid``, ``relation_type``.
        """
        assert self._con is not None

        return self._con.execute(
            """
            WITH triples AS (
                SELECT * FROM read_parquet(?)
            ),
            direct_edges AS (
                SELECT
                    subject AS source_rid,
                    CASE WHEN predicate = 'subClassOf' THEN 'is_a' ELSE predicate END
                        AS relation_type,
                    object AS target_rid
                FROM triples
                WHERE is_resource
                AND object LIKE 'RID%'
                AND predicate != 'type'
            ),
            restriction_edges AS (
                SELECT
                    subclass.subject AS source_rid,
                    on_property.object AS relation_type,
                    some_values.object AS target_rid
                FROM triples AS subclass
                JOIN triples AS restriction_type
                ON restriction_type.subject = subclass.object
                AND restriction_type.predicate = 'type'
                AND restriction_type.object = 'Restriction'
                JOIN triples AS on_property
                ON on_property.subject = subclass.object
                AND on_property.predicate = 'onProperty'
                JOIN triples AS some_values
                ON some_values.subject = subclass.object
                AND some_values.predicate = 'someValuesFrom'
                WHERE subclass.predicate = 'subClassOf'
                AND subclass.is_resource
                AND subclass.object NOT LIKE 'RID%'
            )
            SELECT * FROM direct_edges
            UNION ALL
            SELECT * FROM restriction_edges
            """,
            [str(self.triples_path)],
        ).fetch_arrow_table()

    def _to_networkx(self, nodes: pa.Table, edges: pa.Table) -> nx.DiGraph:
        """Assembles a ``networkx.DiGraph`` from the derived node/edge tables.

        Args:
            nodes: The table produced by :meth:`_query_nodes`.
            edges: The table produced by :meth:`_query_edges`.

        Returns:
            A directed graph with one node per RID (attributes: label, synonyms,
            definition, is_obsolete, replaced_by_rid) and one edge per relation,
            each carrying a ``relation_type`` attribute.
        """
        graph = nx.DiGraph()

        graph.add_nodes_from(
            (
                row["rid"],
                {
                    "label": row["label"],
                    "synonyms": row["synonyms"],
                    "definition": row["definition"],
                    "is_obsolete": row["is_obsolete"],
                    "replaced_by_rid": row["replaced_by_rid"],
                },
            )
            for row in nodes.to_pylist()
        )

        graph.add_edges_from(
            (
                row["source_rid"],
                row["target_rid"],
                {"relation_type": row["relation_type"]},
            )
            for row in edges.to_pylist()
        )

        return graph

    def __enter__(self) -> RadLexGraphBuilder:
        """Allows use as a context manager so the DuckDB connection is always closed.

        Returns:
            This builder instance.
        """
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Closes the DuckDB connection on exiting the ``with`` block, if open."""
        self.close()

    def close(self) -> None:
        """Closes the DuckDB connection, if one is open.

        Safe to call multiple times or before :meth:`load`.
        """
        if self._con is not None:
            self._con.close()
            self._con = None
