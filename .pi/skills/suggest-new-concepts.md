---
name: suggest-new-concepts
description: Propose how each RadLex report finding that is not already in RadLex should be integrated into the graph. Use after extract-radlex-concepts has produced its "terms not in RadLex" list, to record structured integration candidates for later review.
allowed-tools: query_radlex_graph get_concept propose_concept
---

# Suggest New RadLex Concepts

Given the "terms not in RadLex" list from `extract-radlex-concepts`, propose a
potential integration for every one of them — where it should attach in the graph,
and why.

## Steps

1. If `extract-radlex-concepts` already found a closest related RID for a finding,
   use it as a starting point rather than searching from scratch. Otherwise, search
   `query_radlex_graph` (retrying with alternate phrasing) to confirm the finding
   truly isn't in RadLex under different wording, then search for the broader
   anatomical structure or finding category it would fall under.
2. Pick the best existing RID as `parent_rid` — the closest concept this finding
   should attach beneath. Use `get_concept` to confirm the parent's definition
   actually fits before using it.
3. `name` should be the precise RadLex-style term for what the report describes
   (not the raw report sentence, and not a repeat of the parent's label).
4. `rationale` should explain why this is a genuine gap and why the chosen parent
   is the closest existing fit.
5. Look for additional relationships beyond the `is_a` parent. RadLex models typed
   anatomical/structural relations such as `Part_Of`, `Has_Part`, `Branch_Of`,
   `Contained_In`, and `Member_Of`. If the finding text implies one of these — e.g. a
   named vessel or structure that is part of, or branches from, a larger structure
   already in the graph — use `query_radlex_graph`/`get_concept` to find the
   relevant existing RID and include it. Only include a relationship if you found a
   real existing RID for the other end of it; do not guess a RID.
6. Call `propose_concept` with `name`, `parent_rid`, `rationale`, and optionally
   `relationships` (each with a `relationType` and `targetRid`; omit if none apply).
7. Every finding on the "terms not in RadLex" list gets a proposal — do not skip
   any of them.

## Output

**Terms not in RadLex, with potential integration** — one entry per finding: the
finding text, the proposed name, the parent RID/label it attaches under, any
additional relationships, and the rationale.
