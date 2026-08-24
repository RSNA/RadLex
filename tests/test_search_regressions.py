"""Regression tests pinning the concept-search behaviours that are easy to lose.

Each case corresponds to a way the search has actually failed, or would fail under a
plausible configuration change. They guard changes that are otherwise silent: a reindex
without the digit-preserving tokenizer, a rebuild that skips the full-text index, or a
ranking tweak that lets substring noise back to the top.

Every test runs against the committed fixture graph, and additionally against the full
graph on machines that have built one. See ``conftest.py``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import radlex_kg as kg

REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = REPO_ROOT / "tests/data/search_eval.json"


def _cases() -> list[dict]:
    """Loads the hand-labelled evaluation cases.

    Returns:
        The ``cases`` list from the evaluation file.
    """
    return json.loads(EVAL_PATH.read_text())["cases"]


def _top(con, term: str):
    """Returns the best hit for a term, or ``None`` if there were none.

    Args:
        con: Open read-only connection.
        term: The search term.

    Returns:
        The first hit dict, or ``None``.
    """
    hits = kg.search(con, term, limit=5)
    return hits[0] if hits else None


def test_index_is_present_and_current(con):
    """The full-text index must cover every row of ``search_docs``.

    A stale index does not raise; ``match_bm25`` returns NULL for rows it does not know
    about, so recall degrades silently and concepts look absent from the ontology.
    """
    docs = con.execute(f"SELECT count(*) FROM {kg.SEARCH_DOCS_TABLE}").fetchone()[0]
    indexed = con.execute(f"SELECT count(*) FROM {kg.FTS_SCHEMA}.docs").fetchone()[0]
    assert docs > 0
    assert docs == indexed


@pytest.mark.parametrize(
    ("term", "expected_rid"),
    [
        ("C7", "RID6148"),
        ("BI-RADS 4", "RID36030"),
    ],
)
def test_digits_survive_tokenization(con, term, expected_rid):
    """Digit-bearing terms must resolve to the concept whose digits match.

    DuckDB's default FTS ``ignore`` pattern strips digits, which silently breaks the
    11.5% of RadLex labels that carry a meaning-bearing number. Without the override,
    "C7" tokenizes to "c" and returns "cesium".
    """
    top = _top(con, term)
    assert top is not None
    assert top["rid"] == expected_rid


def test_acronym_beats_substring_noise(con):
    """A synonym match must outrank concepts that merely contain the letters.

    Substring search ranked "LUL" 67th of 69, behind "hepatocellular carcinoma", because
    "lul" appears inside "hepatocellular". Anything other than an exact top hit here
    means the tiering has regressed.
    """
    top = _top(con, "LUL")
    assert top is not None
    assert top["rid"] == "RID1327"
    assert top["match_type"] == "exact"


@pytest.mark.parametrize(
    ("term", "expected_rid"),
    [
        ("part-solid nodule", "RID50152"),
        ("hilar adenopathy", "RID3798"),
        ("enlarged lymph nodes", "RID3798"),
        ("opacities", "RID28531"),
        ("crazy paving", "RID43256"),
    ],
)
def test_recall_for_report_phrasing(con, term, expected_rid):
    """Report phrasing that differs from the label must still find the concept.

    These all returned nothing before full-text search, and a MISS here is worse than a
    wrong answer: it reads as evidence of a genuine ontology gap and ends up as a
    duplicate proposal in the candidates file.
    """
    hits = kg.search(con, term, limit=5)
    assert expected_rid in {hit["rid"] for hit in hits}


def test_exact_matches_are_labelled_trustworthy(con):
    """Literal matches must be reported as ``exact``, not merely ranked first.

    The consumer skips verification for ``exact`` hits, so losing the label costs a
    round trip on every lookup even when ranking is unaffected.
    """
    top = _top(con, "pleural effusion")
    assert top is not None
    assert top["rid"] == "RID34539"
    assert top["match_type"] == "exact"


def test_absent_terms_do_not_produce_exact_matches(con):
    """Genuine gaps must not come back labelled ``exact``.

    Full-text search returns something plausible for nearly any query, so the risk is a
    confident-looking match for a concept RadLex does not have. Candidates are fine here;
    a claimed exact match is not.
    """
    for case in _cases():
        if not case.get("expect_miss"):
            continue
        hits = kg.search(con, case["phrase"], limit=5)
        assert not any(h["match_type"] == "exact" for h in hits), case["phrase"]


def test_expect_miss_cases_are_genuinely_absent(con):
    """Every phrase labelled a gap must really be absent, compared after normalization.

    This exists because the "crazy paving" case was wrongly labelled a gap: it was
    verified with ``LIKE '%crazy paving%'``, which cannot match the hyphenated
    "crazy-paving pattern" that RadLex actually has. Comparing raw strings is the bug;
    comparing normalized ones is the fix, and asserting it here stops the evaluation set
    from quietly encoding a false premise again.
    """
    for case in _cases():
        if not case.get("expect_miss"):
            continue
        token = re.sub(r"[^a-z0-9]+", " ", case["phrase"].lower()).strip()
        matches = con.execute(
            """
            SELECT rid FROM nodes
            WHERE regexp_replace(lower(label), '[^a-z0-9]+', ' ', 'g') = ?
               OR len(list_filter(
                   synonyms,
                   s -> regexp_replace(lower(s), '[^a-z0-9]+', ' ', 'g') = ?
               )) > 0
            """,
            [token, token],
        ).fetchall()
        assert not matches, (
            f"{case['phrase']!r} is labelled a gap but matches {matches}"
        )


def test_every_eval_rid_still_exists(con):
    """The hand-labelled evaluation set must stay in step with the graph.

    Expected RIDs were fixed against one build of the ontology; a later RadLex release
    can retire or renumber them, which would quietly turn the evaluation into noise.
    """
    known = {row[0] for row in con.execute("SELECT rid FROM nodes").fetchall()}
    missing = {
        rid for case in _cases() for rid in case["expected_rids"] if rid not in known
    }
    assert not missing


def test_results_only_contain_radlex_concepts(con):
    """Search must never surface the non-RID administrative nodes.

    The full-text index excludes them by construction, so a result carrying one means an
    exact-match path has diverged from the index and is reporting something the rest of
    the system treats as out of scope.
    """
    for term in ("pleural effusion", "nodule", "opacity", "stent"):
        for hit in kg.search(con, term, limit=8):
            assert hit["rid"].startswith("RID"), hit
