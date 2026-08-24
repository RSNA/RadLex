# /// script
# requires-python = ">=3.13"
# dependencies = ["duckdb>=1.5.5"]
# ///
# The inline metadata above (PEP 723) lets `uv run` resolve duckdb itself, so the skill
# works from any working directory rather than only from a synced project checkout. Note
# it must be invoked as `uv run <script>`; `uv run python <script>` treats the file as a
# plain argument and ignores this block. Keep the constraint in step with pyproject.toml:
# the project writes the database and this reads it, and DuckDB's storage format is not
# guaranteed compatible across major versions.
"""Batched, rank-aware access to the RadLex knowledge graph for skill use.

Backs the ``radlex-concepts`` skill. Exists because the per-call CLI in
:mod:`res_radlex_parsing.extraction.tools` costs ~2s of interpreter+graph startup per
invocation and ranks search hits alphabetically, which buries exact matches (searching
``LUL`` ranks the correct concept 67th, behind "hepatocellular carcinoma"). This script
opens DuckDB once per invocation, accepts many terms/RIDs at a time, and scores matches
so the best candidate comes first.

Reads only the persisted ``nodes``/``edges`` tables, so it needs no OWL re-parsing. Edge
lookups go straight to SQL rather than through ``networkx``, which both avoids
``DiGraph`` collapsing multiple relation types between the same pair of concepts and
skips rebuilding a 46k-node graph on every call.

Default paths resolve from this file's location, not the working directory, and
dependencies come from the inline script metadata, so it runs from anywhere::

    uv run .claude/skills/radlex-concepts/scripts/radlex_kg.py search "pulmonary nodule" LUL
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    """Finds the repository root from this script's own location.

    Defaults were previously relative to the working directory, so invoking the skill
    from any subdirectory reported the graph as missing and advised rebuilding one that
    already existed. Anchoring to the script keeps the defaults correct wherever it runs.

    Returns:
        The nearest ancestor directory containing ``pyproject.toml``, or the repository
        root inferred from this file's position under ``.claude/skills/...`` if no marker
        is found.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return here.parents[4]


REPO_ROOT = _repo_root()
DEFAULT_DB_PATH = REPO_ROOT / "data/intermediate/radlex.duckdb"
DEFAULT_CANDIDATES_PATH = REPO_ROOT / "data/output/candidates.jsonl"

SEARCH_DOCS_TABLE = "search_docs"
FTS_SCHEMA = f"fts_main_{SEARCH_DOCS_TABLE}"

# A concept is a candidate when its BM25 score reaches this fraction of the query's best
# BM25 score. Relative rather than absolute because BM25 values are not comparable across
# queries -- an exact match scores 12.9 for one term and 8.9 for another.
#
# 0.7 comes from tests/eval_search.py: accuracy is flat from 0.3 to 0.85, so the choice is
# purely about how much noise the caller wades through (4.4 hits/query at 0.3, 2.8 at 0.7).
# Recall falls off at 0.9. Sitting at 0.7 rather than the last passing value keeps room for
# queries the 19-case evaluation set does not represent.
DEFAULT_BM25_RATIO = 0.7

# Score tiers from _SCORE_SQL: 88+ means the label or a synonym is literally equal to the
# term after normalization, which is the only evidence strong enough to accept unchecked.
EXACT_SCORE_FLOOR = 88
# 55-60 means the term appears as a whole word inside a longer label or synonym.
WORD_MATCH_FLOOR = 55

# Edges whose source is a blank node rather than a concept: the builder's direct_edges
# CTE sweeps up owl:Restriction internals (someValuesFrom) and axiom annotations. They
# make up ~40% of the edges table and are meaningless as concept-to-concept relations.
REAL_RID = "source_rid LIKE 'RID%' AND target_rid LIKE 'RID%'"

# Scoring tiers, highest first. Exact and word-boundary matches must outrank bare
# substring matches, otherwise short terms and acronyms drown in incidental matches
# ("LUL" inside "hepatocellular").
_SCORE_SQL = """
GREATEST(
    CASE WHEN lower(label) = $term THEN 100 ELSE 0 END,
    CASE WHEN norm_label = $norm THEN 96 ELSE 0 END,
    CASE WHEN len(list_filter(synonyms, s -> lower(s) = $term)) > 0 THEN 92 ELSE 0 END,
    CASE WHEN len(list_filter(
        synonyms, s -> regexp_replace(lower(s), '[^a-z0-9]+', ' ', 'g') = $norm
    )) > 0 THEN 88 ELSE 0 END,
    CASE WHEN regexp_matches(norm_label, $word_re) THEN 60 ELSE 0 END,
    CASE WHEN len(list_filter(
        synonyms,
        s -> regexp_matches(regexp_replace(lower(s), '[^a-z0-9]+', ' ', 'g'), $word_re)
    )) > 0 THEN 55 ELSE 0 END,
    CASE WHEN contains(lower(label), $term) THEN 20 ELSE 0 END,
    CASE WHEN len(list_filter(synonyms, s -> contains(lower(s), $term))) > 0
        THEN 15 ELSE 0 END
) AS score
"""


def normalize(text: str) -> str:
    """Collapses punctuation and case so "ground-glass" and "ground glass" compare equal.

    RadLex labels and report text disagree constantly on hyphenation, which otherwise
    turns a real match into a missed one.

    Args:
        text: Raw label, synonym, or search term.

    Returns:
        Lowercased text with every run of non-alphanumeric characters replaced by a
        single space, stripped at both ends.
    """
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Opens the persisted graph database read-only.

    Args:
        db_path: Path to the DuckDB file written by ``RadLexGraphBuilder.save()``.

    Returns:
        An open read-only connection.

    Raises:
        SystemExit: If the database has not been built yet, with instructions for
            building it rather than an opaque DuckDB error.
    """
    if not db_path.exists():
        sys.exit(
            f"RadLex graph not found at {db_path}.\n"
            "If the ontology has not been ingested yet, place RadLex.owl at "
            "data/staging/RadLex.owl and run the parse+build steps from the README.\n"
            "If you expected a graph to exist there, pass --db with its actual path "
            "rather than rebuilding."
        )
    con = duckdb.connect(str(db_path), read_only=True)
    _warn_if_index_stale(con)
    return con


def _warn_if_index_stale(con: duckdb.DuckDBPyConnection) -> None:
    """Warns when the full-text index no longer covers the search table.

    A stale index does not raise: ``match_bm25`` returns NULL for rows it does not know
    about, so searches quietly lose recall and every affected concept looks like it is
    missing from RadLex. That is the exact failure this tool exists to prevent, so it is
    worth two counts per invocation to detect.

    Args:
        con: Open connection to the graph database.
    """
    try:
        docs = con.execute(f"SELECT count(*) FROM {SEARCH_DOCS_TABLE}").fetchone()
        indexed = con.execute(f"SELECT count(*) FROM {FTS_SCHEMA}.docs").fetchone()
    except duckdb.Error:
        logger.warning(
            "No full-text index found; search will fall back to exact matching. "
            "Rebuild the graph to create it."
        )
        return

    if (docs or [0])[0] != (indexed or [0])[0]:
        logger.warning(
            "Full-text index is stale (%s documents indexed, %s in %s). "
            "Rebuild the graph; results are missing concepts.",
            (indexed or [0])[0],
            (docs or [0])[0],
            SEARCH_DOCS_TABLE,
        )


def _lexical_matches(
    con: duckdb.DuckDBPyConnection, term: str, norm: str
) -> dict[str, dict[str, Any]]:
    """Scores concepts by literal label/synonym comparison.

    Args:
        con: Open read-only connection.
        term: The raw search term.
        norm: ``term`` passed through :func:`normalize`.

    Returns:
        A mapping of RID to a row dict carrying the concept's fields and the integer
        ``score`` from the tier table, for every concept scoring above zero.
    """
    rows = con.execute(
        f"""
        WITH scored AS (
            SELECT
                rid, label, synonyms, definition, is_obsolete, replaced_by_rid,
                regexp_replace(lower(label), '[^a-z0-9]+', ' ', 'g') AS norm_label
            FROM nodes
            WHERE label IS NOT NULL AND rid LIKE 'RID%'
        ),
        ranked AS (
            SELECT rid, label, synonyms, definition, is_obsolete, replaced_by_rid,
                   {_SCORE_SQL}
            FROM scored
        )
        SELECT rid, label, synonyms, definition, is_obsolete, replaced_by_rid, score
        FROM ranked
        WHERE score > 0
        ORDER BY score DESC
        """,
        {
            "term": term.lower(),
            "norm": norm,
            "word_re": rf"\b{re.escape(norm)}\b",
        },
    ).fetchall()

    cols = [
        "rid",
        "label",
        "synonyms",
        "definition",
        "is_obsolete",
        "replaced_by_rid",
        "score",
    ]
    return {row[0]: dict(zip(cols, row)) for row in rows}


def _bm25_matches(
    con: duckdb.DuckDBPyConnection, term: str, pool: int = 50
) -> dict[str, float]:
    """Scores concepts by BM25 over the persisted full-text index.

    Aggregates with ``max`` across a concept's label and synonyms: each is indexed as
    its own document, and a concept should be judged on its best-matching term rather
    than penalized for having many.

    Args:
        con: Open read-only connection.
        term: The raw search term.
        pool: How many top-scoring concepts to retrieve before the caller applies its
            relative cutoff. Disjunctive BM25 matches very broadly — nearly 2,000
            concepts for "part-solid nodule", since "part" and "node" appear
            everywhere — so retrieving all of them would be wasteful.

    Returns:
        A mapping of RID to BM25 score, or an empty mapping if the full-text index is
        unavailable.
    """
    try:
        rows = con.execute(
            f"""
            SELECT rid, max(sc) AS bm25
            FROM (
                SELECT rid, {FTS_SCHEMA}.match_bm25(doc_id, ?) AS sc
                FROM {SEARCH_DOCS_TABLE}
            )
            WHERE sc IS NOT NULL
            GROUP BY rid
            ORDER BY bm25 DESC
            LIMIT ?
            """,
            [term, pool],
        ).fetchall()
    except duckdb.Error:
        # The index is missing, or the fts extension was never installed on this
        # machine. Exact matching still works, so degrade rather than fail — but say
        # so, since silently reduced recall looks exactly like a genuine ontology gap.
        logger.warning(
            "Full-text search unavailable; falling back to exact matching only. "
            "Rebuild the graph, or check that the fts extension is installed."
        )
        return {}

    return {rid: score for rid, score in rows}


def search(
    con: duckdb.DuckDBPyConnection,
    term: str,
    limit: int = 8,
    bm25_ratio: float = DEFAULT_BM25_RATIO,
) -> list[dict[str, Any]]:
    """Finds concepts matching a term, best match first.

    Combines two kinds of evidence. Literal label/synonym equality is the only thing
    strong enough to accept without checking, so it is reported as ``exact``. Everything
    else — BM25 hits and partial word matches — is a ``candidate`` to verify, because
    BM25 will always return something plausible for any query.

    The candidate cutoff is relative to the strongest BM25 hit for this particular
    query, not an absolute floor: BM25 scores depend on term rarity and document length,
    so the same absolute value means different things for different queries.

    Args:
        con: Open read-only connection.
        term: Free text from the report, e.g. "part-solid pulmonary nodule" or "LUL".
        limit: Maximum hits to return.
        bm25_ratio: A concept is a candidate when its BM25 score is at least this
            fraction of the query's best BM25 score.

    Returns:
        Hit dicts with ``rid``, ``label``, ``synonyms``, ``definition``,
        ``is_obsolete``, ``replaced_by_rid``, ``match_type`` (``exact``/``candidate``/
        ``weak``), the lexical ``score``, and ``bm25`` where full-text matched. Ordered
        exact first, then candidates by BM25, then weak.
    """
    norm = normalize(term)
    if not norm:
        return []

    lexical = _lexical_matches(con, term, norm)
    bm25 = _bm25_matches(con, term)

    cutoff = max(bm25.values()) * bm25_ratio if bm25 else 0.0

    hits: list[dict[str, Any]] = []
    for rid in set(lexical) | set(bm25):
        row = lexical.get(rid)
        if row is None:
            row = _node_row(con, rid)
            if row is None:
                continue
            row["score"] = 0

        score = row["score"]
        bm25_score = bm25.get(rid)

        if score >= EXACT_SCORE_FLOOR:
            match_type = "exact"
        elif score >= WORD_MATCH_FLOOR or (
            bm25_score is not None and bm25_score >= cutoff
        ):
            match_type = "candidate"
        else:
            match_type = "weak"

        hits.append({**row, "match_type": match_type, "bm25": bm25_score})

    # Substring-only hits are what produced "LUL" -> "hepatocellular carcinoma"; they are
    # noise whenever anything better exists, so they only appear if nothing else did.
    if any(h["match_type"] != "weak" for h in hits):
        hits = [h for h in hits if h["match_type"] != "weak"]

    rank = {"exact": 0, "candidate": 1, "weak": 2}
    hits.sort(
        key=lambda h: (
            rank[h["match_type"]],
            -h["score"] if h["match_type"] == "exact" else 0,
            # Obsolete concepts often win on BM25 alone -- "stent" matches the retired
            # RID5598 more tightly than the live "vascular stent" -- so break ties
            # toward the live concept before falling back to score.
            h["is_obsolete"],
            -(h["bm25"] or 0.0),
            len(h["label"] or ""),
        )
    )
    return hits[:limit]


def _node_row(con: duckdb.DuckDBPyConnection, rid: str) -> dict[str, Any] | None:
    """Fetches the node fields for a RID matched by full text but not lexically.

    Args:
        con: Open read-only connection.
        rid: The RadLex identifier to fetch.

    Returns:
        A row dict with the same keys :func:`_lexical_matches` produces (minus
        ``score``), or ``None`` if the RID is absent.
    """
    row = con.execute(
        "SELECT rid, label, synonyms, definition, is_obsolete, replaced_by_rid "
        "FROM nodes WHERE rid = ?",
        [rid],
    ).fetchone()
    if row is None:
        return None

    cols = ["rid", "label", "synonyms", "definition", "is_obsolete", "replaced_by_rid"]
    return dict(zip(cols, row))


def concept(con: duckdb.DuckDBPyConnection, rid: str) -> dict[str, Any] | None:
    """Looks up one concept with its neighbours already resolved to labels.

    Returning bare RIDs would force a follow-up lookup per neighbour just to find out
    what they mean, so parents, children, and typed relations all carry labels here.

    Args:
        con: Open read-only connection.
        rid: RadLex identifier, e.g. ``"RID1327"``.

    Returns:
        A dict with the concept's attributes plus ``parents`` and ``children``
        (``is_a`` neighbours, each ``{rid, label}``) and ``relations`` (non-hierarchy
        edges, each ``{relation_type, rid, label}``), or ``None`` if the RID is absent.
    """
    row = con.execute(
        "SELECT rid, label, synonyms, definition, is_obsolete, replaced_by_rid "
        "FROM nodes WHERE rid = ?",
        [rid],
    ).fetchone()
    if row is None:
        return None

    parents = con.execute(
        f"""
        SELECT e.target_rid, n.label FROM edges e LEFT JOIN nodes n ON n.rid = e.target_rid
        WHERE e.source_rid = ? AND e.relation_type = 'is_a' AND {REAL_RID}
        ORDER BY n.label
        """,
        [rid],
    ).fetchall()

    children = con.execute(
        f"""
        SELECT e.source_rid, n.label FROM edges e LEFT JOIN nodes n ON n.rid = e.source_rid
        WHERE e.target_rid = ? AND e.relation_type = 'is_a' AND {REAL_RID}
        ORDER BY n.label
        LIMIT 40
        """,
        [rid],
    ).fetchall()

    relations = con.execute(
        f"""
        SELECT e.relation_type, e.target_rid, n.label
        FROM edges e LEFT JOIN nodes n ON n.rid = e.target_rid
        WHERE e.source_rid = ? AND e.relation_type <> 'is_a' AND {REAL_RID}
        ORDER BY e.relation_type, n.label
        LIMIT 40
        """,
        [rid],
    ).fetchall()

    return {
        "rid": row[0],
        "label": row[1],
        "synonyms": row[2],
        "definition": row[3],
        "is_obsolete": row[4],
        "replaced_by_rid": row[5],
        "parents": [{"rid": r, "label": lab} for r, lab in parents],
        "children": [{"rid": r, "label": lab} for r, lab in children],
        "relations": [
            {"relation_type": rel, "rid": r, "label": lab} for rel, r, lab in relations
        ],
    }


def ancestors(
    con: duckdb.DuckDBPyConnection, rid: str, max_depth: int = 12
) -> list[dict[str, str]]:
    """Walks ``is_a`` edges upward to show where a concept sits in the hierarchy.

    Placing a proposed concept sensibly depends on seeing the chain above a candidate
    parent, not just the parent itself.

    Args:
        con: Open read-only connection.
        rid: Starting RadLex identifier.
        max_depth: Maximum number of levels to climb, guarding against cycles.

    Returns:
        A list of ``{rid, label}`` from the starting concept upward, nearest first.
    """
    chain: list[dict[str, str]] = []
    seen: set[str] = set()
    current = rid

    for _ in range(max_depth):
        if current in seen:
            break
        seen.add(current)
        row = con.execute("SELECT label FROM nodes WHERE rid = ?", [current]).fetchone()
        if row is None:
            break
        chain.append({"rid": current, "label": row[0]})
        parent = con.execute(
            f"SELECT target_rid FROM edges WHERE source_rid = ? "
            f"AND relation_type = 'is_a' AND {REAL_RID} LIMIT 1",
            [current],
        ).fetchone()
        if parent is None:
            break
        current = parent[0]

    return chain


class ProposalError(ValueError):
    """Raised when a candidate concept references something the graph does not contain."""


def validate_proposal(
    con: duckdb.DuckDBPyConnection,
    name: str,
    parent_rid: str,
    rationale: str,
    relationships: list[dict[str, str]],
) -> None:
    """Checks a candidate against the graph before it reaches the review file.

    A proposal is only useful to a reviewer if its anchors resolve. An invented or
    mistyped ``parent_rid`` makes the candidate unplaceable, and since proposals are
    appended rather than rewritten, a bad record is permanent until someone edits the
    file by hand. Catching it here costs one lookup.

    Relation types are checked against the types the ontology actually uses rather than a
    hard-coded list, so the check stays correct across RadLex releases and still catches
    plausible-looking inventions like ``PartOf`` for ``Part_Of``.

    Args:
        con: Open read-only connection to the graph.
        name: Proposed RadLex-style term.
        parent_rid: RID the candidate should attach beneath via ``is_a``.
        rationale: Justification for the proposal.
        relationships: Non-hierarchy relations, each ``{"relation_type", "target_rid"}``.

    Raises:
        ProposalError: If a required field is blank, a referenced RID is absent from the
            graph, or a relation type is not one the ontology uses.
    """
    if not name.strip():
        raise ProposalError("name must not be empty")
    if not rationale.strip():
        raise ProposalError("rationale must not be empty; it is all a reviewer gets")

    referenced = {parent_rid} | {r.get("target_rid", "") for r in relationships}
    rows = con.execute(
        "SELECT rid FROM nodes WHERE rid IN (SELECT unnest(?::VARCHAR[]))",
        [sorted(referenced)],
    ).fetchall()
    missing = referenced - {row[0] for row in rows}
    if missing:
        raise ProposalError(
            f"referenced RIDs not in the graph: {', '.join(sorted(missing))}. "
            "Look the concept up with the 'search' or 'concept' command first."
        )

    known_types = {
        row[0]
        for row in con.execute(
            "SELECT DISTINCT relation_type FROM edges WHERE source_rid LIKE 'RID%'"
        ).fetchall()
    }
    bad_types = {r.get("relation_type", "") for r in relationships} - known_types
    if bad_types:
        raise ProposalError(
            f"relation types not used by RadLex: {', '.join(sorted(bad_types))}. "
            f"Check the 'relations' field of a nearby concept for the correct spelling."
        )


def propose(
    con: duckdb.DuckDBPyConnection,
    name: str,
    parent_rid: str,
    rationale: str,
    relationships: list[dict[str, str]],
    candidates_path: Path,
) -> dict[str, Any]:
    """Validates a candidate concept and appends it to the review file.

    Args:
        con: Open read-only connection to the graph, used for validation.
        name: Proposed RadLex-style term for the new concept.
        parent_rid: RID the candidate should attach beneath via ``is_a``.
        rationale: Why this is a genuine gap and why that parent is the closest fit.
        relationships: Non-hierarchy relations, each ``{"relation_type", "target_rid"}``.
        candidates_path: JSONL file to append to; parent directory is created.

    Returns:
        The record that was written.

    Raises:
        ProposalError: If the candidate fails :func:`validate_proposal`.
    """
    validate_proposal(con, name, parent_rid, rationale, relationships)

    record = {
        "name": name,
        "parent_rid": parent_rid,
        "rationale": rationale,
        "relationships": relationships,
    }
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    with candidates_path.open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    return record


def _scalar(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    """Runs a counting query and returns the number.

    ``fetchone`` yields ``None`` when a query produces no row, so subscripting its result
    directly turns an empty or malformed database into a ``TypeError`` rather than a
    number the caller can report.

    Args:
        con: Open read-only connection.
        sql: A query selecting exactly one integer column.

    Returns:
        The value, or ``0`` if the query returned no row.
    """
    row = con.execute(sql).fetchone()
    return int(row[0]) if row is not None else 0


def _emit(payload: Any) -> None:
    """Prints a JSON payload to stdout for the caller to read.

    Args:
        payload: Any JSON-serializable structure.
    """
    json.dump(payload, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    """Parses arguments and dispatches to the requested subcommand.

    Args:
        argv: Argument list, defaulting to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser(
        "search", help="Rank concepts matching one or more terms."
    )
    p_search.add_argument("terms", nargs="+")
    p_search.add_argument("--limit", type=int, default=8)
    p_search.add_argument(
        "--bm25-ratio",
        type=float,
        default=DEFAULT_BM25_RATIO,
        help="Candidate cutoff as a fraction of the query's best BM25 score.",
    )

    p_concept = sub.add_parser("concept", help="Look up one or more RIDs in full.")
    p_concept.add_argument("rids", nargs="+")

    p_anc = sub.add_parser(
        "ancestors", help="Show the is_a chain above one or more RIDs."
    )
    p_anc.add_argument("rids", nargs="+")

    p_propose = sub.add_parser(
        "propose", help="Append candidate concepts to the review file."
    )
    p_propose.add_argument(
        "--json",
        required=True,
        help='JSON array of {"name","parent_rid","rationale","relationships"} objects.',
    )
    p_propose.add_argument(
        "--candidates-path", type=Path, default=DEFAULT_CANDIDATES_PATH
    )

    sub.add_parser("check", help="Verify the graph is built and report its size.")

    args = parser.parse_args(argv)

    con = connect(args.db)
    try:
        if args.command == "search":
            _emit(
                {
                    term: search(con, term, args.limit, args.bm25_ratio)
                    for term in args.terms
                }
            )
        elif args.command == "concept":
            _emit({rid: concept(con, rid) for rid in args.rids})
        elif args.command == "ancestors":
            _emit({rid: ancestors(con, rid) for rid in args.rids})
        elif args.command == "propose":
            records = json.loads(args.json)
            # Validate every record before writing any of them. Appends cannot be undone,
            # so a half-written batch would leave the reviewer sorting good records from
            # bad by hand.
            try:
                for record in records:
                    validate_proposal(
                        con,
                        record["name"],
                        record["parent_rid"],
                        record["rationale"],
                        record.get("relationships", []),
                    )
            except (ProposalError, KeyError) as error:
                _emit({"written": 0, "error": str(error)})
                return 1

            written = [
                propose(
                    con,
                    record["name"],
                    record["parent_rid"],
                    record["rationale"],
                    record.get("relationships", []),
                    args.candidates_path,
                )
                for record in records
            ]
            _emit(
                {
                    "written": len(written),
                    "path": str(args.candidates_path),
                    "records": written,
                }
            )
        elif args.command == "check":
            _emit(
                {
                    "db": str(args.db),
                    "concepts": _scalar(con, "SELECT count(*) FROM nodes"),
                    "usable_edges": _scalar(
                        con, f"SELECT count(*) FROM edges WHERE {REAL_RID}"
                    ),
                }
            )
    finally:
        con.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
