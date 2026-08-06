"""Shared DuckDB connection and schema helpers for the RadLex knowledge graph store.

Centralizes the on-disk DuckDB schema (``nodes``/``edges`` tables) and connection
handling so both the graph-building stage and later query code operate on the same
table definitions.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pyarrow as pa

logger = logging.getLogger(__name__)

NODES_TABLE = "nodes"
EDGES_TABLE = "edges"


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
