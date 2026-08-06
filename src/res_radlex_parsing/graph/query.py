"""Query helpers for the persisted RadLex knowledge graph.

Reconstructs a ``networkx.DiGraph`` directly from the ``nodes``/``edges`` tables
written by :class:`res_radlex_parsing.graph.build_graph.RadLexGraphBuilder` — no OWL
re-parsing or triples re-derivation — and exposes the read operations used by the
extraction/suggestion skills: text/synonym search (via DuckDB), get node by RID, and
get parents/children (via the reconstructed graph).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import duckdb
import networkx as nx
import pyarrow as pa

from res_radlex_parsing._shared import db

logger = logging.getLogger(__name__)


class RadLexGraphQuery:
    """Loads the persisted RadLex knowledge graph from DuckDB and answers lookups.

    Methods are designed for chaining/context-manager use, e.g.::

        with RadLexGraphQuery(db_path).load() as query:
            matches = query.search("pulmonary nodule")

    Attributes:
        db_path: Filesystem path to the persisted DuckDB database file.
    """

    def __init__(self, db_path: Path) -> None:
        """Initializes the query helper without connecting to anything.

        Args:
            db_path: Filesystem path to the persisted DuckDB database file, as
                written by :meth:`RadLexGraphBuilder.save`.
        """
        self.db_path = db_path
        self._con: duckdb.DuckDBPyConnection | None = None
        self._graph: nx.DiGraph | None = None

    def __enter__(self) -> RadLexGraphQuery:
        """Allows use as a context manager so the DuckDB connection is always closed.

        Returns:
            This query instance.
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

    def load(self) -> RadLexGraphQuery:
        """Opens a DuckDB connection and reconstructs the graph from persisted tables.

        Reads the ``nodes`` and ``edges`` tables directly (no OWL parsing, no triples
        Parquet involved) and builds an in-memory ``networkx.DiGraph`` from them.

        Returns:
            This query instance, to support chaining.

        Raises:
            OSError: If ``db_path`` cannot be read.
        """
        if not self.db_path.exists():
            raise OSError(f"Database file not found:  {self.db_path}")

        self._con = db.connect(self.db_path, read_only=True)
        nodes = self._con.execute(f"SELECT * FROM {db.NODES_TABLE}").fetch_arrow_table()
        edges = self._con.execute(f"SELECT * FROM {db.EDGES_TABLE}").fetch_arrow_table()
        self._graph = self._to_networkx(nodes, edges)

        return self

    def search(self, text: str, limit: int = 10) -> pa.Table:
        """Searches node labels and synonyms for a text match.

        Args:
            text: Free text to match against node labels/synonyms (case-insensitive
                substring match).
            limit: Maximum number of matching nodes to return.

        Returns:
            A table with columns ``rid``, ``label``, ``synonyms``, ranked by match
            relevance, at most ``limit`` rows.

        Raises:
            RuntimeError: If called before :meth:`load`.
        """
        if self._con is None:
            raise RuntimeError("load() must be called before search()")

        return self._con.execute(
            f"""
            SELECT rid, label, synonyms
            FROM {db.NODES_TABLE}
            WHERE label ILIKE '%' || ? || '%'
                OR list_contains(
                    list_transform(synonyms, x -> lower(x)), lower(?)
                )
            ORDER BY label
            LIMIT ?
            """,
            [text, text, limit],
        ).fetch_arrow_table()

    def get_node(self, rid: str) -> dict[str, Any] | None:
        """Looks up a single node's attributes by RID.

        Args:
            rid: The RadLex identifier to look up.

        Returns:
            A dict of the node's attributes (label, synonyms, definition,
            is_obsolete, replaced_by_rid), or ``None`` if ``rid`` is not in the
            graph.

        Raises:
            RuntimeError: If called before :meth:`load`.
        """
        if self._graph is None:
            raise RuntimeError("load() must be called before get node()")

        if rid not in self._graph:
            return None

        return dict(self._graph.nodes[rid])

    def get_parents(self, rid: str, relation_type: str = "is_a") -> list[str]:
        """Gets the RIDs a node points to via a given relation type.

        Args:
            rid: The RadLex identifier whose parents to look up.
            relation_type: The edge relation type to follow (default ``"is_a"`` for
                ontology hierarchy parents; other typed relations, e.g.
                ``"Part_Of"``, can be passed to traverse non-hierarchy edges).

        Returns:
            RIDs of nodes reachable from ``rid`` via a single outgoing edge of the
            given relation type.

        Raises:
            RuntimeError: If called before :meth:`load`.
        """
        if self._graph is None:
            raise RuntimeError("load() must be called before get_parents()")

        return [
            target
            for target in self._graph.successors(rid)
            if self._graph[rid][target]["relation_type"] == relation_type
        ]

    def get_children(self, rid: str, relation_type: str = "is_a") -> list[str]:
        """Gets the RIDs that point to a node via a given relation type.

        Args:
            rid: The RadLex identifier whose children to look up.
            relation_type: The edge relation type to follow (default ``"is_a"`` for
                ontology hierarchy children).

        Returns:
            RIDs of nodes with a single outgoing edge of the given relation type
            pointing at ``rid``.

        Raises:
            RuntimeError: If called before :meth:`load`.
        """
        if self._graph is None:
            raise RuntimeError("load() must be called before get_children()")

        return [
            source
            for source in self._graph.predecessors(rid)
            if self._graph[source][rid]["relation_type"] == relation_type
        ]

    def _to_networkx(self, nodes: pa.Table, edges: pa.Table) -> nx.DiGraph:
        """Assembles a ``networkx.DiGraph`` from the nodes/edges tables.

        Args:
            nodes: Rows from the persisted ``nodes`` table.
            edges: Rows from the persisted ``edges`` table.

        Returns:
            A directed graph matching the structure built by
            :meth:`RadLexGraphBuilder._to_networkx`.
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
