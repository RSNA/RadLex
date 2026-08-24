"""Builds the small committed graph fixture the regression tests run against.

The real graph is a 9.7 MB gitignored artifact, so a clean checkout had nothing to test
with and the whole regression suite skipped — reporting green while protecting nothing.
This carves a few thousand concepts out of the full graph into two Parquet files small
enough to commit. The tests assemble a real DuckDB graph from them at session start, which
keeps the repository ~28x smaller than committing the built database (83 KB against
2.4 MB, most of which is DuckDB block and full-text index overhead) and has the useful side
effect of exercising the index build on every test run.

Selection is driven by what the tests actually need to discriminate. Every RID named in
``search_eval.json`` is included, along with its ``is_a`` ancestry, plus the *distractors*
that make each assertion meaningful: without "hepatocellular carcinoma" present, the "LUL"
test cannot show that exact matching beats substring noise, and without "cesium" the
digit-tokenizer test proves nothing. A random remainder gives BM25 usable corpus
statistics.

BM25 scores here will not equal production scores — inverse document frequency and average
document length both depend on corpus size. The tests therefore assert *which* concept wins,
never a score value.

Regenerate after changing the evaluation set, then commit both Parquet files::

    uv run python tests/data/build_fixture.py
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DB = REPO_ROOT / "data/intermediate/radlex.duckdb"
FIXTURE_NODES = REPO_ROOT / "tests/data/fixture_nodes.parquet"
FIXTURE_EDGES = REPO_ROOT / "tests/data/fixture_edges.parquet"
EVAL_PATH = REPO_ROOT / "tests/data/search_eval.json"

# Concepts that must be present for a test to prove anything, beyond the answers
# themselves. Each entry is a term whose *competitors* need to exist in the fixture.
DISTRACTOR_TERMS = (
    "lul",  # hepatocellular carcinoma, acellular membrane -- substring noise
    "c7",  # cesium, C6/C7, C7/T1 -- digit-stripping collisions
    "bi-rads",  # categories 4B/4C must not outrank 4
    "crazy",  # crazy-paving pattern and sign
    "stent",  # obsolete RID5598 vs live vascular stent
    "spiculated",
    "nodule",
    "opacit",  # opacity, opacities, ground-glass opacity
    "lymphadenopathy",
    "adenopathy",
    "lower lobe",
    "pleural effusion",
    "emphysema",
    "vertebra",
    "pancreas",
)

RANDOM_SAMPLE = 2000


def _seed_rids(con: duckdb.DuckDBPyConnection) -> set[str]:
    """Collects the RIDs the fixture must contain.

    Args:
        con: Open connection to the full graph.

    Returns:
        Every RID named in the evaluation set, plus concepts whose label or synonyms
        contain a distractor term.
    """
    cases = json.loads(EVAL_PATH.read_text())["cases"]
    rids = {rid for case in cases for rid in case["expected_rids"]}

    for term in DISTRACTOR_TERMS:
        rows = con.execute(
            """
            SELECT rid FROM nodes
            WHERE label ILIKE '%' || ? || '%'
               OR len(list_filter(synonyms, s -> lower(s) LIKE '%' || ? || '%')) > 0
            """,
            [term, term],
        ).fetchall()
        rids.update(row[0] for row in rows)

    return rids


def _with_ancestry(con: duckdb.DuckDBPyConnection, rids: set[str]) -> set[str]:
    """Adds every ``is_a`` ancestor of the given concepts.

    The ``ancestors`` helper walks to the ontology root, so a fixture missing the upper
    hierarchy would make that path untestable.

    Args:
        con: Open connection to the full graph.
        rids: Starting concept ids.

    Returns:
        ``rids`` plus all reachable ``is_a`` ancestors.
    """
    con.execute(
        "CREATE OR REPLACE TEMP TABLE seed AS SELECT unnest(?::VARCHAR[]) AS rid",
        [list(rids)],
    )
    rows = con.execute(
        """
        WITH RECURSIVE up(rid) AS (
            SELECT rid FROM seed
            UNION
            SELECT e.target_rid
            FROM up JOIN edges e ON e.source_rid = up.rid
            WHERE e.relation_type = 'is_a' AND e.target_rid LIKE 'RID%'
        )
        SELECT rid FROM up
        """
    ).fetchall()
    return {row[0] for row in rows}


def _relation_targets(con: duckdb.DuckDBPyConnection, rids: set[str]) -> set[str]:
    """Adds the targets of non-``is_a`` relations one hop out from the seed concepts.

    Without them the fixture keeps the source concept but drops the edge, so relation
    types like ``Part_Of`` vanish from the subset entirely — and proposal validation,
    which checks relation types against the ones the graph actually uses, would reject
    valid input when run against the fixture.

    Args:
        con: Open connection to the full graph.
        rids: Concepts already selected.

    Returns:
        Targets of typed relations leaving those concepts.
    """
    rows = con.execute(
        """
        SELECT DISTINCT target_rid FROM edges
        WHERE source_rid IN (SELECT unnest(?::VARCHAR[]))
          AND relation_type <> 'is_a'
          AND source_rid LIKE 'RID%' AND target_rid LIKE 'RID%'
        """,
        [sorted(rids)],
    ).fetchall()
    return {row[0] for row in rows}


def main() -> int:
    """Builds and writes the fixture database.

    Returns:
        Process exit code.
    """
    if not SOURCE_DB.exists():
        raise SystemExit(
            f"Source graph not found at {SOURCE_DB}. Build the full pipeline first."
        )

    source = duckdb.connect(str(SOURCE_DB), read_only=True)
    try:
        rids = _with_ancestry(source, _seed_rids(source))
        rids |= _relation_targets(source, rids)

        # Deterministic filler so BM25 has a corpus to compute statistics against.
        # Ordering by rid keeps regeneration reproducible; a random sample would make the
        # committed fixture churn on every rebuild.
        filler = source.execute(
            """
            SELECT rid FROM nodes
            WHERE label IS NOT NULL AND rid LIKE 'RID%' AND rid NOT IN (SELECT rid FROM seed)
            ORDER BY rid
            LIMIT ?
            """,
            [RANDOM_SAMPLE],
        ).fetchall()
        rids.update(row[0] for row in filler)

        nodes = source.execute(
            "SELECT * FROM nodes WHERE rid IN (SELECT unnest(?::VARCHAR[]))",
            [list(rids)],
        ).to_arrow_table()
        edges = source.execute(
            """
            SELECT * FROM edges
            WHERE source_rid IN (SELECT unnest(?::VARCHAR[]))
              AND target_rid IN (SELECT unnest(?::VARCHAR[]))
            """,
            [list(rids), list(rids)],
        ).to_arrow_table()
    finally:
        source.close()

    writer = duckdb.connect()
    try:
        writer.register("fixture_nodes", nodes)
        writer.register("fixture_edges", edges)
        writer.execute(
            f"COPY fixture_nodes TO '{FIXTURE_NODES}' (FORMAT parquet, COMPRESSION zstd)"
        )
        writer.execute(
            f"COPY fixture_edges TO '{FIXTURE_EDGES}' (FORMAT parquet, COMPRESSION zstd)"
        )
    finally:
        writer.close()

    total_kb = (FIXTURE_NODES.stat().st_size + FIXTURE_EDGES.stat().st_size) / 1024
    print(
        f"{nodes.num_rows} concepts, {edges.num_rows} edges -> "
        f"{FIXTURE_NODES.name} + {FIXTURE_EDGES.name}, {total_kb:.0f} KB total"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
