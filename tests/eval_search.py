"""Measures concept-search quality against the hand-labelled evaluation set.

Not collected by pytest (the filename does not start with ``test_``); this is the tuning
harness behind the ``--bm25-ratio`` default. Run it from the repository root::

    uv run python tests/eval_search.py

Compares three arms so the hybrid design has to justify itself rather than being assumed:

- ``lexical``  — exact/word/substring tiers only, i.e. behaviour before full-text search.
- ``bm25``     — full-text only, no lexical tiers.
- ``hybrid@R`` — both, with the candidate cutoff at fraction ``R`` of the query's best
  BM25 score.

If ``bm25`` matches ``hybrid`` across the board, the lexical tiers are not earning their
complexity and the design should collapse to full-text plus an exact-match flag.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / ".claude/skills/radlex-concepts/scripts"),
)

import radlex_kg as kg

EVAL_PATH = Path("tests/data/search_eval.json")
RATIOS = (0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9)


def _hits(
    con: Any, phrase: str, arm: str, ratio: float, limit: int = 5
) -> list[dict[str, Any]]:
    """Runs one arm of the comparison for a single phrase.

    Args:
        con: Open read-only connection to the graph database.
        phrase: The report phrase to look up.
        arm: One of ``lexical``, ``bm25``, or ``hybrid``.
        ratio: Candidate cutoff fraction, used by the ``hybrid`` arm only.
        limit: Maximum hits to return.

    Returns:
        Hit dicts as produced by :func:`radlex_kg.search`, or an equivalent shape for
        the single-source arms.
    """
    if arm == "hybrid":
        return kg.search(con, phrase, limit=limit, bm25_ratio=ratio)

    norm = kg.normalize(phrase)
    if arm == "lexical":
        rows = kg._lexical_matches(con, phrase, norm)
        ranked = sorted(
            rows.values(),
            key=lambda r: (-r["score"], r["is_obsolete"], len(r["label"] or "")),
        )
        return [
            {
                **r,
                "match_type": "exact"
                if r["score"] >= kg.EXACT_SCORE_FLOOR
                else "candidate",
            }
            for r in ranked[:limit]
        ]

    scores = kg._bm25_matches(con, phrase)
    ranked_rids = sorted(scores, key=lambda r: -scores[r])[:limit]
    out = []
    for rid in ranked_rids:
        row = kg._node_row(con, rid)
        if row is not None:
            out.append(
                {**row, "score": 0, "bm25": scores[rid], "match_type": "candidate"}
            )
    return out


def evaluate(
    con: Any, cases: list[dict[str, Any]], arm: str, ratio: float
) -> dict[str, Any]:
    """Scores one arm across every evaluation case.

    Two different questions are being asked, so they are counted separately. For cases
    with expected RIDs, did the top hit land inside the accepted set? For cases where a
    miss is correct, did the arm avoid claiming an exact match it cannot support?

    Args:
        con: Open read-only connection to the graph database.
        cases: Parsed ``cases`` list from the evaluation file.
        arm: One of ``lexical``, ``bm25``, or ``hybrid``.
        ratio: Candidate cutoff fraction for the ``hybrid`` arm.

    Returns:
        A summary dict with ``hit_at_1``, ``findable``, ``miss_ok``, ``miss_total``,
        ``trusted_ok``/``trusted_wrong`` (see below) and a ``failures`` list naming the
        phrases that missed.

    ``trusted_ok`` and ``trusted_wrong`` count the cases the arm labelled ``exact``,
    split by whether that label was justified. They are the reason hit@1 alone cannot
    decide between arms: an arm that finds the right concept but cannot say whether to
    trust it forces the consumer to verify every hit, and every verification is another
    chance to accept something wrong.
    """
    hit = findable = miss_ok = miss_total = trusted_ok = trusted_wrong = 0
    in_set = 0
    returned = 0
    failures: list[str] = []

    for case in cases:
        hits = _hits(con, case["phrase"], arm, ratio)
        top = hits[0] if hits else None
        returned += len(hits)

        if case.get("expect_miss"):
            miss_total += 1
            if not any(h["match_type"] == "exact" for h in hits):
                miss_ok += 1
            else:
                trusted_wrong += 1
                failures.append(f"{case['phrase']!r} claimed a false exact match")
            continue

        findable += 1
        if any(h["rid"] in case["expected_rids"] for h in hits):
            in_set += 1
        correct = top is not None and top["rid"] in case["expected_rids"]

        # An obsolete concept surfacing first is fine provided the replacement it points
        # at is the accepted answer -- the consumer contract is to follow replaced_by_rid.
        if not correct and top is not None and top.get("is_obsolete"):
            correct = top.get("replaced_by_rid") in case["expected_rids"]

        if correct:
            hit += 1
            if top is not None and top["match_type"] == "exact":
                trusted_ok += 1
        else:
            if top is not None and top["match_type"] == "exact":
                trusted_wrong += 1
            got = f"{top['rid']} {top['label']!r}" if top else "MISS"
            failures.append(f"{case['phrase']!r} -> {got}")

    return {
        "hit_at_1": hit,
        "findable": findable,
        "miss_ok": miss_ok,
        "miss_total": miss_total,
        "trusted_ok": trusted_ok,
        "trusted_wrong": trusted_wrong,
        "in_set": in_set,
        "returned": returned,
        "failures": failures,
    }


def main() -> int:
    """Runs every arm and prints a comparison table.

    Returns:
        Process exit code.
    """
    cases = json.loads(EVAL_PATH.read_text())["cases"]
    con = kg.connect(kg.DEFAULT_DB_PATH)
    try:
        arms = [("lexical", 0.0), ("bm25", 0.0)] + [("hybrid", r) for r in RATIOS]
        results = []
        for arm, ratio in arms:
            name = f"hybrid@{ratio}" if arm == "hybrid" else arm
            results.append((name, evaluate(con, cases, arm, ratio)))

        print(
            f"{'arm':<14} {'hit@1':<9} {'correct-miss':<14} "
            f"{'trusted-ok':<12} {'FALSE-trust':<13} {'in-set':<9} {'hits/query':<10}"
        )
        print("-" * 72)
        for name, r in results:
            print(
                f"{name:<14} {r['hit_at_1']}/{r['findable']:<7} "
                f"{r['miss_ok']}/{r['miss_total']:<12} "
                f"{r['trusted_ok']:<12} {r['trusted_wrong']:<13} "
                f"{r['in_set']}/{r['findable']:<6} {r['returned'] / len(cases):<10.1f}"
            )

        for name, r in results:
            if r["failures"]:
                print(f"\n{name} failures:")
                for failure in r["failures"]:
                    print(f"  {failure}")
    finally:
        con.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
