"""Shared fixtures: a graph built from committed Parquet, plus the real graph when present.

The regression suite used to point only at ``data/intermediate/radlex.duckdb``, which is
gitignored. On a clean checkout every test skipped and the suite reported green while
protecting nothing. Tests now run against a small committed subset by default, and
additionally against the full graph on machines that have built it.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest
from _pytest.mark.structures import ParameterSet

from res_radlex_parsing._shared import db

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / ".claude/skills/radlex-concepts/scripts"
sys.path.insert(0, str(SCRIPTS))

FIXTURE_NODES = REPO_ROOT / "tests/data/fixture_nodes.parquet"
FIXTURE_EDGES = REPO_ROOT / "tests/data/fixture_edges.parquet"
REAL_DB = REPO_ROOT / "data/intermediate/radlex.duckdb"


@pytest.fixture(scope="session")
def fixture_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Assembles a real DuckDB graph from the committed Parquet subset.

    Built rather than committed because the Parquet pair is ~138 KB against 2.4 MB for
    the equivalent database, nearly all of which is DuckDB block and full-text index
    overhead. Building here also means every run exercises
    :func:`res_radlex_parsing._shared.db.build_search_index` rather than trusting a
    snapshot of its output.

    Args:
        tmp_path_factory: pytest's session-scoped temporary directory factory.

    Returns:
        Path to the assembled database.
    """
    path = tmp_path_factory.mktemp("radlex-fixture") / "graph.duckdb"
    con = db.connect(path)
    try:
        con.execute(
            f"CREATE OR REPLACE TABLE {db.NODES_TABLE} AS SELECT * FROM read_parquet(?)",
            [str(FIXTURE_NODES)],
        )
        con.execute(
            f"CREATE OR REPLACE TABLE {db.EDGES_TABLE} AS SELECT * FROM read_parquet(?)",
            [str(FIXTURE_EDGES)],
        )
        db.build_search_index(con)
    finally:
        con.close()

    return path


def _graph_params() -> list[ParameterSet]:
    """Lists the graphs to run each test against.

    Returns:
        The committed fixture always, plus the full graph when it has been built locally
        — the fixture keeps CI honest, the full graph catches anything that only shows up
        at real corpus size.
    """
    params = [pytest.param("fixture", id="fixture")]
    if REAL_DB.exists():
        params.append(pytest.param("real", id="full-graph"))
    return params


@pytest.fixture(scope="session", params=_graph_params())
def graph_path(request: pytest.FixtureRequest, fixture_db: Path) -> Path:
    """Resolves the graph path for the current parametrization.

    Args:
        request: pytest request carrying the parametrized graph name.
        fixture_db: The assembled fixture database.

    Returns:
        Path to the graph under test.
    """
    return fixture_db if request.param == "fixture" else REAL_DB


@pytest.fixture(scope="session")
def con(graph_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Opens one read-only connection per graph under test.

    Args:
        graph_path: Path to the graph under test.

    Yields:
        An open read-only connection.
    """
    connection = duckdb.connect(str(graph_path), read_only=True)
    yield connection
    connection.close()
