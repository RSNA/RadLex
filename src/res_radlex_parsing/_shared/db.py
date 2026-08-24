"""Shared DuckDB connection and schema helpers for the RadLex knowledge graph store.

Centralizes the on-disk DuckDB schema (``nodes``/``edges``/``search_docs`` tables), the
full-text search index over ``search_docs``, and connection handling, so the
graph-building stage and later query code operate on the same definitions.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pyarrow as pa

logger = logging.getLogger(__name__)

NODES_TABLE = "nodes"
EDGES_TABLE = "edges"
SEARCH_DOCS_TABLE = "search_docs"

# DuckDB names the generated index schema after the indexed table.
FTS_SCHEMA = f"fts_main_{SEARCH_DOCS_TABLE}"

# DuckDB's default ignore pattern is '(\\.|[^a-z])+', which deletes every digit at both
# index and query time. 11.5% of RadLex labels carry a meaning-bearing digit (vertebral
# levels, BI-RADS categories, T1/T2 weighting, isotopes); without this override "C7"
# tokenizes to "c" and returns "cesium" rather than the literal C7 concept.
FTS_IGNORE_PATTERN = r"(\.|[^a-z0-9])+"


def connect(db_path: Path, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Opens a DuckDB connection to the on-disk RadLex graph database.

    Creates the parent directory for ``db_path`` if it does not already exist. Does
    not create tables — see :func:`create_schema`.

    Args:
        db_path: Filesystem path to the DuckDB database file.
        read_only: If ``True``, opens the connection read-only, allowing multiple
            concurrent readers (e.g. several tool-call subprocesses, or a notebook
            open at the same time) instead of taking an exclusive write lock.

    Returns:
        An open connection to the database at ``db_path``.

    Raises:
        OSError: If the parent directory cannot be created or the file cannot be
            opened.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Connecting to DuckDB database at %s (read_only=%s)", db_path, read_only
    )
    return duckdb.connect(str(db_path), read_only=read_only)


def create_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Creates the ``nodes`` and ``edges`` tables if they do not already exist.

    Args:
        con: An open DuckDB connection, as returned by :func:`connect`.
    """
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {NODES_TABLE} (
            rid VARCHAR PRIMARY KEY,
            label VARCHAR,
            synonyms VARCHAR[],
            definition VARCHAR,
            is_obsolete BOOLEAN,
            replaced_by_rid VARCHAR
        )
        """
    )
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {EDGES_TABLE} (
            source_rid VARCHAR,
            target_rid VARCHAR,
            relation_type VARCHAR,
            PRIMARY KEY (source_rid, target_rid, relation_type)
        )
        """
    )


def write_nodes(con: duckdb.DuckDBPyConnection, nodes: pa.Table) -> None:
    """Replaces the contents of the ``nodes`` table with the given data.

    Uses ``CREATE OR REPLACE TABLE ... AS SELECT``, so the table is fully rebuilt from
    ``nodes`` on each call (suitable for a from-scratch ontology rebuild, not an
    incremental upsert). Note this replaces the table definition entirely, including
    the primary key constraint created by :func:`create_schema`.

    Call :func:`build_search_index` afterwards. The full-text index derives from this
    table and does not update itself; leaving it stale makes searches silently return
    nothing rather than fail.

    Args:
        con: An open DuckDB connection, as returned by :func:`connect`.
        nodes: A table with columns ``rid``, ``label``, ``synonyms``, ``definition``,
            ``is_obsolete``, ``replaced_by_rid``.
    """
    con.register("nodes_view", nodes)
    try:
        con.execute(
            f"CREATE OR REPLACE TABLE {NODES_TABLE} AS SELECT * FROM nodes_view"
        )
    finally:
        con.unregister("nodes_view")


def write_edges(con: duckdb.DuckDBPyConnection, edges: pa.Table) -> None:
    """Replaces the contents of the ``edges`` table with the given data.

    Uses ``CREATE OR REPLACE TABLE ... AS SELECT``, so the table is fully rebuilt from
    ``edges`` on each call (suitable for a from-scratch ontology rebuild, not an
    incremental upsert). Note this replaces the table definition entirely, including
    the primary key constraint created by :func:`create_schema`.

    Args:
        con: An open DuckDB connection, as returned by :func:`connect`.
        edges: A table with columns ``source_rid``, ``target_rid``, ``relation_type``.
    """
    con.register("edges_view", edges)
    try:
        con.execute(
            f"CREATE OR REPLACE TABLE {EDGES_TABLE} AS SELECT * FROM edges_view"
        )
    finally:
        con.unregister("edges_view")


def build_search_index(con: duckdb.DuckDBPyConnection) -> None:
    """Rebuilds the ``search_docs`` table and its full-text index from ``nodes``.

    Must run after :func:`write_nodes`, since it derives from that table. Callers that
    write nodes by some other route are responsible for calling this too — see
    :func:`search_index_is_stale` for the guard that detects when they have not.

    One row per searchable string (the label, plus each synonym unnested) rather than
    one concatenated document per concept: BM25 penalizes long documents, so
    concatenating a concept's synonyms would rank well-annotated concepts *worse*.
    Query-side, aggregate with ``max`` per RID.

    Concepts with no English label, and the handful of node ids that are not RadLex
    RIDs, are excluded so full-text results cannot surface entries that the exact-match
    path filters out.

    Args:
        con: An open writable DuckDB connection, as returned by :func:`connect`.

    Raises:
        duckdb.Error: If the ``fts`` extension cannot be installed or loaded.
    """
    con.execute("INSTALL fts; LOAD fts;")
    # Rebuilding the documents and the index over them are two writes, and a failure
    # between them leaves the table describing concepts the index has never seen. That
    # state does not raise on read -- match_bm25 simply returns NULL for the rows it does
    # not know -- so it surfaces as concepts silently missing from search. Commit both or
    # neither.
    con.execute("BEGIN TRANSACTION")
    try:
        _write_search_index(con)
    except Exception:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")

    count = con.execute(f"SELECT count(*) FROM {SEARCH_DOCS_TABLE}").fetchone()
    logger.info(
        "Built full-text index over %s search documents", count[0] if count else 0
    )


def _write_search_index(con: duckdb.DuckDBPyConnection) -> None:
    """Writes the ``search_docs`` table and creates the index over it.

    Args:
        con: An open writable DuckDB connection, inside a transaction.
    """
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {SEARCH_DOCS_TABLE} AS
        SELECT rid || ':L' AS doc_id, rid, label AS term, 'label' AS kind
        FROM {NODES_TABLE}
        WHERE label IS NOT NULL AND rid LIKE 'RID%'
        UNION ALL
        SELECT rid || ':S' || CAST(i AS VARCHAR), rid, s, 'synonym'
        FROM (
            SELECT rid, unnest(synonyms) AS s, generate_subscripts(synonyms, 1) AS i
            FROM {NODES_TABLE}
            WHERE label IS NOT NULL AND rid LIKE 'RID%'
        )
        WHERE s IS NOT NULL
        """
    )
    con.execute(
        f"""
        PRAGMA create_fts_index(
            '{SEARCH_DOCS_TABLE}', 'doc_id', 'term',
            ignore = '{FTS_IGNORE_PATTERN}',
            overwrite = 1
        )
        """
    )
    count = con.execute(f"SELECT count(*) FROM {SEARCH_DOCS_TABLE}").fetchone()
    logger.info(
        "Built full-text index over %s search documents", count[0] if count else 0
    )


def search_index_is_stale(con: duckdb.DuckDBPyConnection) -> bool:
    """Reports whether the full-text index no longer covers ``search_docs``.

    Worth checking before relying on full-text results: when the index and table
    disagree, ``match_bm25`` returns NULL for the unindexed rows rather than raising, so
    a stale index looks exactly like "this concept is not in RadLex" — the false-gap
    outcome the search work exists to prevent.

    Args:
        con: An open DuckDB connection; read-only is sufficient.

    Returns:
        ``True`` if the index is missing or its document count differs from
        ``search_docs``, ``False`` if they agree.
    """
    try:
        docs = con.execute(f"SELECT count(*) FROM {SEARCH_DOCS_TABLE}").fetchone()
        indexed = con.execute(f"SELECT count(*) FROM {FTS_SCHEMA}.docs").fetchone()
    except duckdb.Error:
        logger.warning("Full-text index not present or unreadable; treating as stale")
        return True

    return (docs or [0])[0] != (indexed or [0])[0]
