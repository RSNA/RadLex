---
name: extract-radlex-concepts
description: Identify radiology findings and concepts in report text and match them to existing RadLex ontology concepts using the RadLex knowledge graph. Use when asked to extract, identify, or match RadLex concepts from a radiology report.
allowed-tools: query_radlex_graph get_concept
---

# Extract RadLex Concepts

Given radiology report text, identify the clinically meaningful findings and match
each one to an existing RadLex concept.

## Steps

1. Read the report text and list candidate findings: anatomical structures,
   observations, measurements, and abnormalities mentioned in the report. Ignore
   boilerplate (headers, patient demographics, signatures).
2. For each candidate finding, call `query_radlex_graph` with the finding's text.
   If the first search returns nothing useful, retry with a shorter or
   differently-worded version of the term (e.g. drop modifiers, try a synonym)
   before giving up on it.
3. For any promising match from `query_radlex_graph`, call `get_concept` on its RID
   to confirm the full definition and check `is_obsolete`. If the concept is
   obsolete, prefer its `replaced_by_rid` (call `get_concept` on that RID instead)
   rather than reporting an obsolete match.
4. Decide, for each finding, whether it is genuinely **in RadLex**: a returned
   concept's label/synonyms/definition must describe the same clinical concept as
   the report text, at the same level of specificity. A loose keyword overlap is
   not enough, and a broader/related concept does not count as a match (e.g. RadLex
   having the vessel but not the specific named branch the report mentions is not a
   match for that branch). If multiple candidates are returned, pick the most
   specific one that still accurately matches (e.g. prefer "part-solid pulmonary
   nodule" over "pulmonary nodule" if the report specifies part-solid).
5. For every finding that is *not* genuinely in RadLex, still note the closest
   related RID found (if any), even though it didn't count as a match — this is
   handed off to `suggest-new-concepts` as a starting point for where the concept
   should be integrated into the graph.

## Output

Report exactly two sections:

**Detected RadLex terms** — one row per matched finding, with its RadLex RID and
label.

**Terms not in RadLex** — one row per finding with no genuine match, with the
closest related RID found (if any) carried forward. Hand this list to the
`suggest-new-concepts` skill, which proposes how each one should be integrated into
the graph.
