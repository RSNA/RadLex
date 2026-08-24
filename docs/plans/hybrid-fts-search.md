# Plan: hybrid exact + BM25 full-text search over the RadLex graph

**Status:** complete — all phases shipped and verified 2026-08-20
**Created:** 2026-08-20
**Revised:** 2026-08-20, after independent review (see *Review outcomes*)
**Owner:** Tarik Alkasab

## Decisions (settled 2026-08-20 by the owner)

1. **Cutoff semantics** — *per-query relative cutoff*. A concept is a `candidate` when its
   BM25 score is at least `ratio × (top BM25 score for that query)`. This sidesteps the
   incomparability of absolute BM25 scores across queries. The flag is `--bm25-ratio`;
   its default is set by Phase 5 measurement, starting from 0.5.
2. **Eval labelling** — *a phrase may map to a set of RIDs*. Headline metric is therefore
   hit@1-in-set and MISS rate, not strict precision@1.
3. **Null-label and non-RID concepts** — *excluded from the index*, so BM25 cannot surface
   what the exact tier promises is filtered out. `search_docs` requires
   `label IS NOT NULL` on both arms and `rid LIKE 'RID%'`.
4. **Stopwords** — *keep DuckDB's `english` default*. No measured harm; revisit only if
   Phase 5 shows stopword-heavy anatomical phrases underperforming.

## Problem

Concept lookup currently fails on ordinary report phrasing, and it fails *silently* — a
term that should match returns nothing or returns noise, and the consuming agent
concludes the concept is missing from RadLex. That false-gap outcome is the worst failure
mode this project has, because it flows straight into `propose_concept` and pollutes
`data/output/candidates.jsonl` with duplicates of concepts RadLex already has.

Two distinct defects produce it.

**`RadLexGraphQuery.search` ranks alphabetically, not by relevance.** It matches
`label ILIKE '%term%'` OR an exact synonym, then sorts by `label` and truncates at
`limit`. Searching `LUL` returns 69 rows; the correct concept (RID1327, *upper lobe of
left lung*) sorts 67th, behind *hepatocellular carcinoma* and *acellular membrane*, which
match only because the letters `lul` appear inside them. At the default limit of 10 the
caller sees pure noise.

**The skill's replacement scorer fixed ranking but not recall.** `radlex_kg.py` scores
exact and word-boundary matches above substring matches, which fixes `LUL`. But it
matches literal words only, so it misses whenever report phrasing differs from the RadLex
label — measured against the graph as built today:

| Query | `radlex_kg.py` today | BM25 prototype | Correct answer |
| --- | --- | --- | --- |
| `opacities` | noise only (plural not stemmed) | ✅ #1 | *opacity* |
| `part-solid nodule` | MISS | ✅ #1 | *part-solid pulmonary nodule* |
| `hilar adenopathy` | MISS | ✅ #1 | *lymphadenopathy* |
| `enlarged lymph nodes` | MISS | ✅ #1 | *lymphadenopathy* |
| `spiculated nodule` | MISS | ⚠️ #2 | *spiculated margin* (#1 is *spiculated*) |
| `LUL` | correct, plus 2 noise hits | ✅ #1, noise gone | *upper lobe of left lung* |

## Goal

Recall good enough that a MISS is real evidence of an ontology gap rather than evidence of
unlucky phrasing, without weakening the confidence signal that stops the agent accepting
coincidental matches.

Out of scope: the `edges` blank-node contamination and `DiGraph` relation collapsing noted
in the README review. Separate concerns, separate plan.

## Design

### Hybrid, not replacement

BM25 alone is not sufficient, because its scores are not comparable across queries — they
depend on term rarity and document length. Both `ground glass opacity` (12.9) and
`pleural effusion` (8.9) are exact matches, yet score differently. No absolute threshold
over BM25 can mean "this is definitely right", and that judgement is what the skill relies
on to decide whether a hit needs verification.

Keep the exact tiers as the confidence signal; add BM25 underneath as the recall layer.

`conjunctive := 1` (require all query terms) is **not** a viable alternative — it returns
zero results for `hilar adenopathy`, destroying the recall win. Disjunctive matching plus
a cutoff is the right shape.

### Replace the numeric scale with an explicit match type

Today `radlex_kg.py` returns a 0–100 `score` and `SKILL.md` documents bands over it (≥88
trust, 55–60 verify, ≤20 noise). BM25 values cannot join that scale honestly. Emit a
categorical `match_type`, with the numeric scores kept alongside as tiebreakers:

| `match_type` | Meaning | Consumer contract |
| --- | --- | --- |
| `exact` | Label or synonym equal after case/punctuation normalization | Trust; confirm sense only |
| `candidate` | BM25 hit above the cutoff | Verify with `concept` before accepting |
| `weak` | Bare substring, no BM25 hit | Treat as noise |

Ordering: all `exact` (by existing 88–100 tiers), then `candidate` by descending BM25,
then `weak`. Within `candidate`, non-obsolete concepts outrank obsolete ones at comparable
scores — BM25 otherwise puts dead concepts first (`stent` → the obsolete RID5598 beats the
live *stent placement*), and 940 concepts are obsolete. `replaced_by_rid` is always
emitted so the consumer can redirect.

Breaking change to the script's output shape and the `SKILL.md` contract; both land in the
same change.

`weak` is populated only when `exact` and `candidate` are both empty, so substring noise
can never dilute a good result set.

### Candidate cutoff

Disjunctive BM25 matches far more than it should: 1,967 concepts for `part-solid nodule`,
452 for `enlarged lymph nodes` — "part" and "node" match nearly everything. Everything
below roughly rank 5 is junk, so a cutoff is required.

Note the tension with the argument above: an absolute BM25 threshold is exactly what this
plan says is meaningless. That is why the cutoff is **relative** (decision 1): a concept is
a candidate when it reaches a fraction of *this query's* best score, so term rarity cancels
out. It is a noise floor either way, never a confidence signal — trust comes only from
`exact`. The flag is `--bm25-ratio`, defaulted to 0.7 by Phase 5 measurement.

### Index shape

FTS indexes a text column, but `nodes.synonyms` is `VARCHAR[]`. Build a `search_docs`
table with one row per searchable string — label, plus each synonym unnested:

```sql
CREATE OR REPLACE TABLE search_docs AS
SELECT rid || ':L' AS doc_id, rid, label AS term, 'label' AS kind
FROM nodes WHERE label IS NOT NULL AND rid LIKE 'RID%'
UNION ALL
SELECT rid || ':S' || CAST(i AS VARCHAR), rid, s, 'synonym'
FROM (
    SELECT rid, unnest(synonyms) AS s, generate_subscripts(synonyms, 1) AS i
    FROM nodes WHERE label IS NOT NULL AND rid LIKE 'RID%'
)
WHERE s IS NOT NULL;

PRAGMA create_fts_index(
    'search_docs', 'doc_id', 'term',
    ignore = '(\.|[^a-z0-9])+',
    overwrite = 1
);
```

One row per term rather than one concatenated document per concept: BM25 penalizes long
documents, so concatenating a concept's synonyms would make well-annotated concepts rank
*worse*. Query-side, aggregate `max(score)` per `rid` (summing would over-rank
synonym-heavy concepts).

**The `ignore` parameter is not optional.** DuckDB's default is `'(\.|[^a-z])+'`, which
deletes every digit at both index and query time. 5,277 of 45,987 labels (11.5%) contain
digits — vertebral levels, BI-RADS categories, T1/T2 weighting, isotopes. With the default
tokenizer, `C7` returns *cesium* even though RadLex has a literal `C7` label (RID6148).
With `[^a-z0-9]`: `C7` → RID6148 first, `T1 vertebra` → *first thoracic vertebra*,
`BI-RADS 4` → *BI-RADS Category 4: Suspicious*, and all five recall wins above still hold.

Measured on the current graph: 69,928 rows after the null-label/non-RID exclusion,
~0.6s to index, database grows 5.5 MB → 9.7 MB, full build 3.0s → 3.6s.

### Placement and staleness

The index must live in the DuckDB file — it cannot be built on the read-only connections
the query layer and skill use, and rebuilding per call would defeat the purpose. It is
written during the graph build, and `search_docs` must be populated *after* `write_nodes`,
since it derives from `nodes`. Read-only BM25 querying against a prebuilt index is
confirmed working.

Building inside `save()` covers the normal path but does **not** make staleness
impossible: `db.write_nodes` is a public documented function that a notebook or future
script can call directly. The failure is silent and indistinguishable from a real gap —
`match_bm25` returns NULL for unindexed doc_ids, i.e. zero hits, no error. So the query
layer also compares `count(*) FROM search_docs` against `count(*) FROM
fts_main_search_docs.docs` and warns on mismatch. Two indexed counts; negligible cost.

## Phases

### Phase 0 — evaluation set (before any code) ✅

Pure data, depends on nothing, and is what the cutoff default must be derived from.
Building it after implementation would mean shipping an arbitrary cutoff and then
rewriting `SKILL.md` when measurement changes it.

- Assemble 3–4 real reports under `tests/data/`, with hand-labelled expected RIDs per
  phrase. Support a *set* of expected RIDs per phrase if decision 2 says so.
- Include deliberately: a digit-bearing query (`C7`, `BI-RADS 4`), an abbreviation RadLex
  lacks (`GGO`), a stopword-heavy anatomical phrase (`head of pancreas`), a known-obsolete
  target (`stent`), and a true gap with no correct RID.

### Phase 1 — schema and build ✅

- `src/res_radlex_parsing/_shared/db.py`
  - Add `SEARCH_DOCS_TABLE = "search_docs"`.
  - Add `build_search_index(con)` executing the DDL and PRAGMA above, including the
    `ignore` parameter.
  - Add `search_index_is_stale(con) -> bool` implementing the count comparison.
  - Extend `create_schema` docstring to note the third table.
- `src/res_radlex_parsing/graph/build_graph.py`
  - Call `db.build_search_index(self._con)` at the end of `save()`, after
    `write_nodes`/`write_edges`.
  - Update the class docstring, which currently claims only nodes/edges are persisted.

**Verify:** rebuild from the existing Parquet; `search_docs` has 70,000 rows with unique
doc_ids; `fts_main_search_docs` exists; `overwrite=1` re-runs cleanly; total build stays
near 3.6s.

### Phase 2 — query layer in the skill script ✅

- `.claude/skills/radlex-concepts/scripts/radlex_kg.py`
  - Rewrite `search()`: compute exact tiers (unchanged SQL), run BM25 for the same term,
    merge by `rid` keeping the strongest evidence, emit `match_type` + `score` + `bm25` +
    `is_obsolete`/`replaced_by_rid`.
  - Apply the obsolete downrank within `candidate`.
  - Add `--bm25-floor` (default from Phase 0/5).
  - Warn on stale index.
  - Degrade to exact-only if FTS is unavailable — wrapping the **BM25 query**, not a
    `LOAD` call. On duckdb 1.5.5 core extensions autoload, so a missing extension surfaces
    at first query; an explicit `load_fts()` helper would be ceremony that catches nothing.

**Verify:** the eight-term chest CT batch; the five MISS cases resolve; `LUL`, `pleural
effusion`, `ground glass opacity`, `centrilobular emphysema`, `spiculated margin`, `left
upper lobe` all keep `exact`; digit queries correct. Batch of eight stays under ~2s.

### Phase 3 — package API parity ✅

- `src/res_radlex_parsing/graph/query.py` — same hybrid ranking in
  `RadLexGraphQuery.search()`, so the documented Python API and the notebook benefit, not
  only the skill. Fix the docstring's claim that results are "ranked by match relevance",
  true only after this change.
- `src/res_radlex_parsing/extraction/tools.py` — no signature change, but update the
  `search_concepts` docstring, which enumerates the returned keys.
- README's usage section documents `query.search(...)`; update if the shape changed.

Ranking logic will now exist in two places. This is a conscious duplication: the skill
script deliberately avoids importing the package because `RadLexGraphQuery.load()`
unconditionally rebuilds a 46k-node networkx graph, which is the ~2s per-call cost the
script exists to avoid. Record that reasoning in both files so it is not "cleaned up"
later.

**Verify:** `notebooks/test_owl_ingest.py` cells still run; the Pi-facing CLI still emits
one JSON object per call.

### Phase 4 — skill and documentation ✅

- `.claude/skills/radlex-concepts/SKILL.md`
  - Replace the score-band table with the `match_type` contract.
  - Drop the plural/word-variant retry advice, now handled by stemming. Keep abbreviation
    expansion — stemming does not help `GGO`, which is genuinely absent.
  - Note that a MISS is now meaningfully stronger evidence of a real gap.
- `README.md` — add `search_docs` + FTS index to the pipeline diagram and the
  `_shared/db.py` bullet; note in Setup that `INSTALL fts` needs network on first run.
- This plan document — keep current as phases land.
- No `CHANGELOG.md` exists. For a pre-release PoC with a single consumer, create one only
  if this ships alongside other user-visible changes. Owner's call.

### Phase 5 — measurement and tuning ✅

- Measure precision@1 (or set-recall, per decision 2) and MISS rate across three arms:
  current scorer, BM25-only, hybrid. **The BM25-only arm is the real test of this design**
  — if it matches hybrid, the exact tiers are not earning their complexity and the design
  should collapse to BM25 plus an exact-match flag.
- Settle the cutoff: fixed floor vs relative vs top-k, on evidence.
- Resolve the `weak`-tier question.
- Add a `pytest` regression pinning the six queries above plus the Phase 0 special cases,
  so a future reindex cannot silently reintroduce false-gap behaviour. Include a
  stemmer-oddity case: porter collides `NOS`-suffixed synonyms with "no".

## Risks

- **Silent staleness.** Mitigated by building inside `save()` *and* the query-time count
  check — the build-time mitigation alone is insufficient, since `write_nodes` is public.
- **Offline first run.** `INSTALL fts` fetches over the network; cached thereafter. Phase
  2's degradation keeps the tool usable meanwhile.
- **Breaking output shape.** Phases 2 and 4 must land together.
- **Over-recall.** BM25 returns a plausible hit for nearly any query, which could push the
  agent toward accepting weak matches. This is why `exact`/`candidate` is preserved and
  why Phase 5 measures MISS rate rather than assuming more recall is better.
- **Tokenizer regressions.** The `ignore` override is load-bearing for 11.5% of concepts
  and easy to lose in a future reindex. Phase 5's regression test must cover it.

## Review outcomes

Independently reviewed 2026-08-20. The DDL, PRAGMA, `overwrite=1` rebuild, read-only
querying, row counts, timings and sizes were all verified working verbatim against a copy
of the real database, as were the motivating defects. Changes made in response:

- **Corrected a wrong claim.** The original said BM25 returned the correct top hit for all
  five MISS cases. False for `spiculated nodule`: *spiculated* (6.03) outranks *spiculated
  margin* (5.25). Table above now reflects this, and it motivated open decision 2.
- **Added the `ignore` tokenizer parameter** (finding 1) — the most consequential change;
  without it 11.5% of concepts are unreachable by their distinguishing digits.
- **Named and resolved the cutoff contradiction** (finding 2) — the plan argued absolute
  BM25 thresholds are meaningless, then introduced one. Now framed explicitly as a noise
  floor, with the alternative to be settled by measurement.
- **Added obsolete downranking** (finding 4), the **query-time staleness check** and a
  weakened claim about staleness being impossible (finding 5), corrected the
  **degradation guard** to wrap the query rather than a `LOAD` (finding 6), and flagged
  the **null-label / non-RID contract mismatch** (finding 7, now open decision 3).
- **Moved the eval set to Phase 0** (finding 8) so the cutoff is derived, not guessed.
- **Recorded the deliberate duplication** of ranking logic between the script and the
  package, with its reason (finding 9).

Preserved as verified sound: hybrid-not-replacement (and the rejection of `conjunctive`),
the `match_type` contract, one-row-per-term index shape, `max(score)` aggregation, and
`weak`-only-when-empty.

## Outcome

Measured over the 19-case evaluation set (`uv run python tests/eval_search.py`):

| arm | hit@1 | correct MISS | labelled trustworthy | false trust | answer in results | hits/query |
| --- | --- | --- | --- | --- | --- | --- |
| lexical (before) | 10/18 | 1/1 | 9 | 0 | 10/18 | 1.7 |
| BM25 only | 16/18 | 1/1 | **0** | 0 | 18/18 | 4.4 |
| **hybrid @ 0.7** | **16/18** | **1/1** | **9** | **0** | **18/18** | **2.8** |

*(Restated 2026-08-24. The original table reported 17 findable cases and 2 correct
MISSes. One of those MISSes was not a MISS: "crazy paving" was labelled an ontology gap
on the strength of a `LIKE '%crazy paving%'` check that cannot match RadLex's hyphenated
"crazy-paving pattern". It is now a findable case, which is why the denominators moved.
The comparison between arms is unaffected.)*

The BM25-only arm did what Phase 5 was designed to test, and the answer was not the one
the metric first suggested. On hit@1 it ties hybrid exactly, which by the plan's own
stated rule would have collapsed the design. But hit@1 cannot see what the exact tier is
for: BM25 alone labels **zero** results trustworthy, so every one of the 18 lookups would
need a verification round trip. Hybrid gets identical recall *and* clears 9 of them for
direct use, with no false trust. The exact tier earns its place on confidence, not
ranking — so the original metric was the flawed part, not the design.

Cutoff set at 0.7. Accuracy is flat from 0.3 to 0.85 and only the result-list length
moves (4.4 hits/query at 0.3, 2.8 at 0.7, 2.5 at 0.85); recall breaks at 0.9. Sitting at
0.7 rather than the last passing value avoids parking on a cliff edge fitted to 19 cases.

Two cases remain failing at hit@1, both arguable rather than broken:

- `spiculated nodule` returns *spiculated* (RID34284) ahead of *spiculated margin*. The
  evaluation set excludes RID34284 on the grounds that it is a descriptor, not a
  report-level finding; that call is worth revisiting.
- `lower lobes` returns *lower lobe of right lung* ahead of the unqualified *lower lobe of
  lung*. Generic-over-specific preference for an unqualified plural is not modelled.

Also shipped, outside the original scope but required to make the above runnable or
correct:

- `pytest` and `ruff` added to the dev dependency group. `CLAUDE.md` prescribes
  `uv run --frozen pytest` and `uv run --frozen ruff`, but neither was installed.
- Repo-wide lint brought to zero: import ordering and four leftover `...` stubs in
  `owl_ingest/parse.py`, `Self` return types on both `__enter__` methods. `notebooks/` is
  now excluded from ruff, since marimo's generated cell protocol (`return (x,)`, bare
  display expressions) is load-bearing and would break if "fixed".

## Completion

- [x] All phases shipped; status set to `complete`.
- [x] README and `SKILL.md` reflect shipped behaviour.
- [x] Regression suite passing: `uv run --frozen pytest` — 11 passed.
- [x] `uv run --frozen ruff check .` — clean.
- [x] Post-review remediation shipped 2026-08-24; see
      `docs/plans/adversarial-code-review-2026-08-23.md` for the findings and
      *Post-review remediation* below for what changed.
- [ ] Owner to decide whether to archive this file to `docs/plans/archive/`.
- [ ] Open: whether to create a `CHANGELOG.md` (deferred, see Phase 4).

## Post-review remediation (2026-08-24)

An independent adversarial review found eight issues, all confirmed. Six were defects
introduced by this work.

- **Evaluation set mislabelled a findable concept as a gap.** The worst of the set,
  because it corrupted the measurement justifying the design. Corrected, and
  `test_expect_miss_cases_are_genuinely_absent` now re-verifies every gap claim with a
  normalized comparison so the same mistake cannot be re-encoded silently.
- **Regression suite protected nothing on a clean checkout.** Its only fixture was the
  gitignored graph, so all tests skipped and reported green. Tests now run against a
  committed Parquet subset (`tests/data/fixture_*.parquet`, 195 KB) assembled into a real
  graph at session start, and additionally against the full graph when present.
- **Non-atomic index rebuild.** `build_search_index` now commits the documents table and
  its index together or not at all. This failure was observed during Phase 1.
- **Staleness guard was dead code.** `search_index_is_stale` was defined, then duplicated
  in the skill script and never called. The package query API now uses it.
- **Package exact tier returned non-RID administrative nodes** the index and skill both
  exclude. Filter added; `test_results_only_contain_radlex_concepts` pins it.
- **Defaults resolved against the working directory**, so invoking the skill from a
  subdirectory reported the graph missing and advised rebuilding an existing one. Paths
  now anchor to the checkout, and the message distinguishes the two cases.
- **Empty results carried a null-typed schema** rather than the documented one.
- **Proposals were written without validation.** `propose` now rejects unknown RIDs,
  relation types RadLex does not use, and blank names or rationales, validating the whole
  batch before writing any of it.

Remaining known gaps: the count-based staleness check cannot detect a same-count content
change, and the two arguable hit@1 failures above are unchanged.
