"""Query helpers for the persisted RadLex knowledge graph.

Reconstructs a ``networkx.DiGraph`` directly from the ``nodes``/``edges`` tables
written by :class:`res_radlex_parsing.graph.build_graph.RadLexGraphBuilder` — no OWL
re-parsing or triples re-derivation — and exposes the read operations used by the
extraction/suggestion skills: text/synonym search (via DuckDB), get node by RID, and
get parents/children (via the reconstructed graph).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Self

import duckdb
import networkx as nx
import pyarrow as pa

from res_radlex_parsing._shared import db

logger = logging.getLogger(__name__)

# Candidate cutoff as a fraction of the query's best BM25 score. Kept in step with the
# skill script's DEFAULT_BM25_RATIO; see tests/eval_search.py for how it was chosen.
#
# The ranking logic is deliberately duplicated between here and
# .claude/skills/radlex-concepts/scripts/radlex_kg.py rather than shared. The skill script
# cannot import this class: :meth:`RadLexGraphQuery.load` rebuilds a 46k-node networkx
# graph on every construction, roughly two seconds, which is exactly the per-call cost the
# script exists to avoid. Keep the two in step by hand.
BM25_RATIO = 0.7

# Returned for queries that normalize to nothing. Built with explicit types rather than
# from empty Python lists, which Arrow would type as null columns -- callers that
# concatenate results or read the schema would then see a different shape from every
# non-empty result.
_RESULT_SCHEMA = pa.schema(
    [
        pa.field("rid", pa.string()),
        pa.field("label", pa.string()),
        pa.field("synonyms", pa.list_(pa.string())),
        pa.field("is_obsolete", pa.bool_()),
        pa.field("replaced_by_rid", pa.string()),
        pa.field("match_type", pa.string()),
        pa.field("bm25", pa.float64()),
    ]
)
_EMPTY_RESULT = _RESULT_SCHEMA.empty_table()


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

    def __enter__(self) -> Self:
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
        nodes = self._con.execute(f"SELECT * FROM {db.NODES_TABLE}").to_arrow_table()
        edges = self._con.execute(f"SELECT * FROM {db.EDGES_TABLE}").to_arrow_table()
        self._graph = self._to_networkx(nodes, edges)

        return self

    def search(self, text: str, limit: int = 10) -> pa.Table:
        """Searches node labels and synonyms for a text match, best match first.

        Ranks by exact label/synonym equality first, then by BM25 over the persisted
        full-text index. Both are needed: exact equality is the only evidence strong
        enough to accept without inspecting the concept, while BM25 supplies the recall
        for report phrasing that does not match a label word for word ("enlarged lymph
        nodes" finds *lymphadenopathy*).

        Falls back to exact matching alone, with a logged warning, when the full-text
        index is absent — a graph built before the index existed still works, with
        reduced recall.

        Args:
            text: Free text to match against node labels/synonyms.
            limit: Maximum number of matching nodes to return.

        Returns:
            A table with columns ``rid``, ``label``, ``synonyms``, ``is_obsolete``,
            ``replaced_by_rid``, ``match_type`` (``exact`` or ``candidate``) and
            ``bm25``, at most ``limit`` rows.

        Raises:
            RuntimeError: If called before :meth:`load`.
        """
        if self._con is None:
            raise RuntimeError("load() must be called before search()")

        normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        if not normalized:
            return _EMPTY_RESULT

        if db.search_index_is_stale(self._con):
            logger.warning(
                "Full-text index does not match %s; search results are incomplete. "
                "Rebuild the graph.",
                db.SEARCH_DOCS_TABLE,
            )

        try:
            return self._hybrid_search(text, normalized, limit)
        except duckdb.Error:
            logger.warning(
                "Full-text index unavailable; falling back to exact matching only. "
                "Rebuild the graph to restore full recall."
            )
            return self._exact_search(text, normalized, limit)

    def _hybrid_search(self, text: str, normalized: str, limit: int) -> pa.Table:
        """Ranks by exact equality first, then BM25 over the full-text index.

        Args:
            text: The raw search text.
            normalized: ``text`` with punctuation collapsed and lowercased.
            limit: Maximum rows to return.

        Returns:
            The ranked result table described by :meth:`search`.

        Raises:
            duckdb.Error: If the full-text index is missing or unreadable.
        """
        assert self._con is not None

        return self._con.execute(
            f"""
            WITH exact AS (
                SELECT rid, 1 AS is_exact
                FROM {db.NODES_TABLE}
                WHERE label IS NOT NULL AND rid LIKE 'RID%' AND (
                    lower(label) = ?
                    OR regexp_replace(lower(label), '[^a-z0-9]+', ' ', 'g') = ?
                    OR len(list_filter(synonyms, s -> lower(s) = ?)) > 0
                    OR len(list_filter(
                        synonyms,
                        s -> regexp_replace(lower(s), '[^a-z0-9]+', ' ', 'g') = ?
                    )) > 0
                )
            ),
            full_text AS (
                SELECT rid, max(sc) AS bm25
                FROM (
                    SELECT rid, {db.FTS_SCHEMA}.match_bm25(doc_id, ?) AS sc
                    FROM {db.SEARCH_DOCS_TABLE}
                )
                WHERE sc IS NOT NULL
                GROUP BY rid
            ),
            merged AS (
                SELECT
                    COALESCE(e.rid, f.rid) AS rid,
                    COALESCE(e.is_exact, 0) AS is_exact,
                    f.bm25
                FROM exact e
                FULL OUTER JOIN full_text f ON f.rid = e.rid
            )
            SELECT
                n.rid, n.label, n.synonyms, n.is_obsolete, n.replaced_by_rid,
                CASE WHEN m.is_exact = 1 THEN 'exact' ELSE 'candidate' END AS match_type,
                m.bm25
            FROM merged m
            JOIN {db.NODES_TABLE} n ON n.rid = m.rid
            WHERE m.is_exact = 1
               OR m.bm25 >= (SELECT max(bm25) * ? FROM full_text)
            ORDER BY m.is_exact DESC, n.is_obsolete ASC, m.bm25 DESC NULLS LAST,
                     length(n.label) ASC
            LIMIT ?
            """,
            [
                text.lower(),
                normalized,
                text.lower(),
                normalized,
                text,
                BM25_RATIO,
                limit,
            ],
        ).to_arrow_table()

    def _exact_search(self, text: str, normalized: str, limit: int) -> pa.Table:
        """Ranks by exact label/synonym equality only, for graphs with no index.

        Args:
            text: The raw search text.
            normalized: ``text`` with punctuation collapsed and lowercased.
            limit: Maximum rows to return.

        Returns:
            A table matching :meth:`search`, with ``bm25`` null throughout.
        """
        assert self._con is not None

        return self._con.execute(
            f"""
            SELECT
                rid, label, synonyms, is_obsolete, replaced_by_rid,
                'exact' AS match_type, NULL::DOUBLE AS bm25
            FROM {db.NODES_TABLE}
            WHERE label IS NOT NULL AND rid LIKE 'RID%' AND (
                lower(label) = ?
                OR regexp_replace(lower(label), '[^a-z0-9]+', ' ', 'g') = ?
                OR len(list_filter(synonyms, s -> lower(s) = ?)) > 0
                OR len(list_filter(
                    synonyms,
                    s -> regexp_replace(lower(s), '[^a-z0-9]+', ' ', 'g') = ?
                )) > 0
            )
            ORDER BY is_obsolete ASC, length(label) ASC
            LIMIT ?
            """,
            [text.lower(), normalized, text.lower(), normalized, limit],
        ).to_arrow_table()

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
