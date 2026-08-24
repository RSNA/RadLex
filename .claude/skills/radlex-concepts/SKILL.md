---
name: radlex-concepts
description: Match findings in radiology report text to RadLex ontology concepts using this repo's RadLex knowledge graph, and propose structured candidates for findings RadLex is missing. Use this whenever a radiology report, impression, or finding text needs concepts identified, coded, matched to RIDs, or checked for ontology coverage — including when the user just pastes report text and asks "what's in RadLex here", asks about a RID, asks what terms are missing from RadLex, or wants gaps written to the candidates file. Also use when exploring the RadLex graph itself (looking up a concept, its parents, or its Part_Of/Branch_Of relations).
allowed-tools: Bash, Read, Write
---

# RadLex concept extraction and gap proposal

Two phases over the RadLex knowledge graph built by this repo:

1. **Extract** — find the clinically meaningful findings in report text and match each to
   an existing RadLex concept.
2. **Propose** — for findings with no genuine match, work out where they *should* attach
   in the graph and record them as review candidates.

Phase 1 is read-only and always safe to run. Phase 2 appends to
`data/output/candidates.jsonl`, so run it only when the user asks for proposals, gaps to
be recorded, or explicitly asks for both phases. If phase 1 surfaces gaps and the user
hasn't asked for proposals, list them and offer phase 2 rather than writing the file.

## Setup

Paths resolve from the script's own location and its dependencies are declared inline, so
these work from any working directory — no synced project environment required. Invoke it
as `uv run <script>`, not `uv run python <script>`: the latter ignores the inline
dependency declaration and will fail with a missing `duckdb`.

```bash
uv run .claude/skills/radlex-concepts/scripts/radlex_kg.py check
```

If that reports the graph is missing, the ontology has not been ingested yet. Building it
takes two steps and about 45 seconds (see `README.md`): place the RadLex OWL export at
`data/staging/RadLex.owl`, then run `RadLexOwlParser(...).load().parse().save(...)`
followed by `RadLexGraphBuilder(...).load().build().save()`. Don't attempt phase 1 until
`check` succeeds — every lookup depends on it.

## The three operations

`scripts/radlex_kg.py` replaces the three tools the Pi harness registered
(`query_radlex_graph`, `get_concept`, `propose_concept`). It takes **many arguments per
call**, which matters: the equivalent per-call CLI in
`src/res_radlex_parsing/extraction/tools.py` costs ~2s of startup each, so a report with
twenty findings turns into minutes of waiting. Batch aggressively — one call per phase is
usually enough.

```bash
S=.claude/skills/radlex-concepts/scripts/radlex_kg.py

# Rank concepts matching each term. Results are keyed by term.
# Combines exact label/synonym matching with BM25 full-text search over the ontology.
uv run $S search "pulmonary nodule" "LUL" "pleural effusion" --limit 5

# Full record for each RID: synonyms, definition, obsolescence, is_a parents and
# children, and typed relations (Part_Of, Branch_Of, ...) — all with labels attached.
uv run $S concept RID50149 RID1327

# The is_a chain upward, for judging where a proposed concept belongs.
uv run $S ancestors RID50152

# Phase 2 only. Appends to data/output/candidates.jsonl.
uv run $S propose --json '[{"name": "...", "parent_rid": "RID...",
  "rationale": "...", "relationships": [{"relation_type": "Part_Of", "target_rid": "RID..."}]}]'
```

`propose` validates before writing anything. Every `parent_rid` and `target_rid` must
exist in the graph, every `relation_type` must be one RadLex actually uses, and `name` and
`rationale` must be non-empty. If any record in the batch fails, nothing is written and
the error names what was wrong — fix it and re-run rather than proposing around it. This
matters because the file is append-only: a candidate pointing at an invented RID cannot be
reviewed and stays there until someone edits it by hand.

## Reading `match_type`

Every hit carries a `match_type`. It is the difference between a result you can act on
and one you have to check, so read it before believing anything:

| `match_type` | What it means | How to treat it |
| --- | --- | --- |
| `exact` | The label or one of the synonyms is literally the search term, ignoring case, punctuation and hyphens | Accept it; only confirm the clinical sense fits |
| `candidate` | Full-text search found it, or the term appears as a whole word inside a longer label | Look it up with `concept` before accepting |
| `weak` | Bare substring coincidence; only ever appears when nothing better was found | Treat as noise |

The distinction matters because full-text search will return something plausible for
almost any query. A ranked list of `candidate` hits is a set of leads, not an answer —
confirming them with `concept` is what separates a real match from a confident-looking
wrong one.

Hits also carry a numeric `score` (lexical tier) and `bm25` (full-text strength). These
rank results; they are not thresholds you should reason about. `bm25` in particular is
not comparable between queries — an exact match scores 12.9 on one term and 8.9 on
another — so never compare a `bm25` value from one search against another.

## Searching well

Search handles plurals, hyphenation, and word order, so these are wasted retries:

- `opacities` already finds *opacity*, `spiculated margins` finds *spiculated margin* —
  stemming covers plural and inflected forms.
- "ground glass", "ground-glass", and "Ground Glass" are all normalized to the same
  thing.
- Word-for-word phrasing is not required: `enlarged lymph nodes` finds *lymphadenopathy*
  with no shared words at all.

What still needs your judgement:

- **Expand abbreviations.** RadLex carries some as synonyms (`LUL` → *upper lobe of left
  lung*, `exact`) but not others — `GGO` genuinely returns nothing, while "ground glass
  opacity" is an `exact` match. Stemming cannot help here, so always try the expansion
  before calling an abbreviation a gap.
- **Drop modifiers to find the neighbourhood.** If a long phrase returns only weak
  candidates, search the head noun. Even when the specific term is absent, the broader
  hit is the anchor phase 2 needs.
- **Follow obsolescence.** A hit with `is_obsolete: true` may still rank first — the
  retired concept *stent* matches the word more tightly than the live *vascular stent*.
  Look up its `replaced_by_rid` and report the replacement.

Because recall is now good, a genuine MISS is meaningfully stronger evidence of a real
ontology gap than it used to be. It is still worth one abbreviation-expansion retry
before you conclude anything.

## Phase 1 — extract

1. Read the report and list candidate findings: anatomical structures, observations,
   measurements, abnormalities. Skip boilerplate — headers, demographics, technique
   sections, signatures.
2. Search all candidates in one batched call. Collect the misses and re-search them in a
   second batch using the rephrasing tactics above.
3. Call `concept` on every promising RID (batched) to read the definition and check
   obsolescence.
4. Decide whether each finding is *genuinely* in RadLex. The concept's label, synonyms, or
   definition must describe the same clinical concept at the same level of specificity.
   Loose keyword overlap doesn't count, and a broader concept is not a match for a
   narrower one — RadLex having a vessel but not the specific named branch the report
   mentions means that branch is a gap. Where several candidates fit, take the most
   specific one that is still accurate: prefer "part-solid pulmonary nodule" over
   "pulmonary nodule" when the report says part-solid.
5. For each finding with no genuine match, note the closest related RID anyway. That
   anchor is what makes phase 2 possible, and finding it now costs nothing extra.

Report two sections:

**Detected RadLex terms** — one row per matched finding: the report text, RID, and label.

**Terms not in RadLex** — one row per unmatched finding, carrying the closest related RID
and label found.

## Phase 2 — propose

Every finding on the "terms not in RadLex" list gets a proposal. Skipping the awkward ones
defeats the point: the whole exercise is discovering where the ontology falls short, and
the awkward cases are usually the interesting ones.

1. Start from the closest related RID that phase 1 already found rather than searching
   again. If there is none, search for the broader category the finding falls under.
2. Choose `parent_rid` — the closest existing concept the finding should sit beneath. Run
   `ancestors` on your candidate parent to confirm the chain above it actually fits; a
   parent that looks right in isolation is often sitting under an unexpected branch.
3. Write `name` as the precise RadLex-style term for what the report describes — not the
   raw report sentence, and not a restatement of the parent's label.
4. Write `rationale` covering both why this is a real gap and why that parent is the
   closest existing fit. A reviewer reading `candidates.jsonl` months later has only this
   sentence to go on.
5. Add relationships beyond `is_a` where the finding implies one. RadLex models typed
   relations — `Part_Of`, `Has_Part`, `Branch_Of`, `Regional_Part_Of`, `Contained_In`,
   `Member_Of`, `Continuous_With`, and others. The `relations` field returned by `concept`
   on the parent usually shows you the right pattern to mirror. Only include a
   relationship when you have a real RID for the other end — never invent one.
6. Write all candidates in a single `propose` call, then report what was recorded. Never
   invent a RID to fill a field — validation rejects the whole batch, and a guessed anchor
   is worse than an omitted relationship.

Report one section:

**Terms not in RadLex, with proposed integration** — per finding: the finding text, the
proposed name, the parent RID and label, any additional relationships, and the rationale.

## Known data quirks

Worth knowing when results look strange:

- 965 concepts have a null `label` (no English `rdfs:label`). They are excluded from
  search entirely, but can still surface as a parent or relation target with a null
  label.
- About 40% of rows in the `edges` table have a blank-node source rather than a concept —
  leftovers from unresolved `owl:Restriction` blocks. This script filters them out, so
  edge counts here won't match a raw `SELECT count(*) FROM edges`.
- Definitions are sparse. A missing definition is normal and is not evidence that a
  concept is wrong or obsolete.
