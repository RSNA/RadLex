# Adversarial Code Review — 2026-08-23

## Objective

Adversarially review the repository, with particular attention to all staged, unstaged, and untracked changes relative to the current `HEAD`. Report only evidence-backed, actionable findings; do not modify product code as part of the review.

## Plan

- [x] Record this review plan in the repository.
- [x] Inventory repository guidance, branch state, worktree changes, architecture, dependencies, and test/lint/type-check entry points.
- [x] Research current primary documentation and upstream behavior for the technologies touched by the changes.
- [x] Review every uncommitted change and its surrounding call paths for correctness, security, data integrity, concurrency, compatibility, error handling, and maintainability risks.
- [x] Exercise focused tests and static checks that can validate or falsify suspected issues; investigate all failures relevant to the final assessment.
- [x] Review committed code paths materially coupled to the changes and scan the broader codebase for analogous or interacting defects.
- [x] Reconcile documentation: update this plan with the completed scope and evidence, review `CHANGELOG.md`/`DEV_LOG.md` if present, and record whether any user-facing documentation change is warranted.
- [x] Deliver findings ordered by severity, with precise file/line references, impact, triggering conditions, and concise remediation guidance; explicitly state residual risks and test gaps.

## Scope Assumptions

- The comparison baseline is the current `HEAD`.
- All staged, unstaged, and untracked files are in scope unless the user identifies generated or intentionally experimental exclusions.
- The requested output is a review, not implementation of fixes.

## Completion Record

Completed 2026-08-23.

- Reviewed all tracked diffs and all author-created untracked files. This review plan itself was excluded from the product assessment.
- Consulted current first-party DuckDB documentation for FTS persistence, refresh behavior, transactions, and Python read-only connections, plus current first-party Claude Code skill documentation for discovery and path handling.
- Validation completed:
  - `uv run --frozen pytest -q` — 11 passed against the local gitignored graph.
  - `uv run --frozen ruff check .` — passed.
  - `uv lock --check` — passed.
  - Full graph build and indexed query against a temporary DuckDB database — passed.
  - Exact-only fallback against a temporary database with the FTS schema removed — passed.
  - Package/skill search comparison across the evaluation corpus — one ordering difference, no membership difference in the first five results.
  - Adversarial temporary-database checks reproduced stale-index false mappings, an undetected same-count node/index divergence, and the non-RID exact-result contract violation.
  - Invocation from a repository subdirectory reproduced both documented skill-command path failures.
- Findings prepared for handoff:
  - Non-atomic graph persistence can pair new nodes with an old FTS index after a failed rebuild.
  - The staleness check cannot detect node/search content changes and is not used by the package query API.
  - The clean-checkout test suite skips every search regression because its only fixture is gitignored.
  - The Claude skill and helper defaults fail outside the repository root.
  - The package exact tier returns a non-RID administrative node that the index and skill deliberately exclude.
  - The evaluation set labels existing `crazy-paving` concepts as a true ontology gap and its MISS metric does not detect that error.
  - Candidate proposal writes do not validate referenced RIDs or relationship types.
  - Punctuation-only searches return an Arrow table with an all-null schema rather than the documented stable schema.
- Documentation reconciliation:
  - No `CHANGELOG.md` or `DEV_LOG.md` exists.
  - `docs/plans/hybrid-fts-search.md`, `README.md`, the skill documentation, and the regression/evaluation documentation require corrections alongside the eventual fixes. They were not edited because this task is review-only.

## Resolution — 2026-08-24

All eight findings were independently reproduced and then fixed. Details of each change
are in `docs/plans/hybrid-fts-search.md` under *Post-review remediation*; the outcome
table in that plan was restated because one finding invalidated its denominators.

| Finding | Resolution |
| --- | --- |
| Non-atomic graph persistence | `build_search_index` wraps the documents table and its index in one transaction |
| Staleness check unused by the package API, cannot see content changes | `RadLexGraphQuery.search` now calls `search_index_is_stale`; the count-only limitation remains and is documented |
| Clean-checkout suite skips every regression | Committed Parquet fixture (195 KB) assembled into a real graph per session; suite also runs against the full graph when present |
| Skill defaults fail outside the repository root | Paths anchor to the checkout via a `pyproject.toml` marker search; the not-found message no longer advises rebuilding an existing graph |
| Package exact tier returns a non-RID node | `rid LIKE 'RID%'` added to both exact paths, pinned by `test_results_only_contain_radlex_concepts` |
| Evaluation set labels existing `crazy-paving` concepts as a gap | Relabelled as findable; `test_expect_miss_cases_are_genuinely_absent` re-verifies every gap claim with a normalized comparison |
| Proposal writes do not validate | `validate_proposal` rejects unknown RIDs, unused relation types, and blank name/rationale; the batch is validated before any record is written |
| Punctuation-only search returns an all-null schema | Empty result built from an explicit Arrow schema, pinned by `test_empty_search_keeps_the_normal_schema` |

Verification after the changes: `uv run --frozen pytest` — 43 passed (21 on the committed
fixture alone, i.e. what a clean checkout runs); `uv run --frozen ruff check .` — clean.

Residual risk unchanged from the review: the staleness check remains count-based, so a
node/index divergence that preserves row count is still undetected.
