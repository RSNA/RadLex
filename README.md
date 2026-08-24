# res_radlex_parsing

Proof-of-concept pipeline that parses the [RadLex](https://www.rsna.org/radlex) radiology
ontology (OWL/RDF-XML) into a queryable knowledge graph, then uses an LLM agent harness
([Pi](https://github.com/earendil-works/pi)) to extract known RadLex concepts from a
radiology report and propose candidate concepts not yet in the ontology.

## How it fits together

```
data/staging/RadLex.owl
        │  RadLexOwlParser (owl_ingest/parse.py)
        ▼
data/intermediate/radlex_triples.parquet   (flat RDF triples table)
        │  RadLexGraphBuilder (graph/build_graph.py)
        ▼
data/intermediate/radlex.duckdb            (nodes/edges/search_docs + FTS index)
        │  RadLexGraphQuery (graph/query.py)
        ▼
extraction/tools.py  ──►  .pi/extensions/radlex_tools.ts  ──►  Pi skills
                                                                 │
                                                                 ▼
                                                data/output/candidates.jsonl
```

- **`src/res_radlex_parsing/owl_ingest/parse.py`** — reads `RadLex.owl` with `rdflib` and
  flattens every RDF triple into a Parquet table (`subject`, `predicate`, `object`,
  `is_resource`, `lang`). No OWL reasoning, no graph semantics — pure triple extraction.
- **`src/res_radlex_parsing/graph/build_graph.py`** — runs SQL over the triples Parquet
  (via DuckDB) to derive `nodes` (RID, label, synonyms, definition, obsolescence) and
  `edges` (`is_a` plus restriction-derived relations like `Part_Of`, `Has_Part`,
  `Branch_Of`) tables, builds an in-memory `networkx.DiGraph`, and persists the tables to
  a DuckDB file. Also builds `search_docs` (one row per label/synonym) and a DuckDB FTS
  index over it, so concept lookup can rank by BM25 rather than alphabetically.
- **`src/res_radlex_parsing/graph/query.py`** — reloads the DuckDB tables into a
  `networkx.DiGraph` and exposes read operations: text/synonym `search`, `get_node`,
  `get_parents`, `get_children`.
- **`src/res_radlex_parsing/_shared/db.py`** — shared DuckDB connection/schema helpers
  used by both the builder and the query layer, plus `build_search_index()` and the
  staleness guard for the full-text index.
- **`src/res_radlex_parsing/extraction/tools.py`** — a `click` CLI
  (`search`, `get-concept`, `propose-concept`) that wraps `RadLexGraphQuery` and appends
  to `data/output/candidates.jsonl`. Invoked as a subprocess by the Pi extension below;
  each subcommand prints one JSON object to stdout.
- **`.pi/extensions/radlex_tools.ts`** and **`.pi/skills/*.md`** — the Pi harness pieces:
  the extension shells out to `extraction/tools.py`; the skills
  (`extract-radlex-concepts.md`, `suggest-new-concepts.md`) drive an LLM agent to match
  report findings to RadLex concepts and propose new ones.
- **`notebooks/test_owl_ingest.py`** — a [marimo](https://marimo.io) notebook for
  interactively exercising the ingest/build/query pipeline.

## Data layout

`data/` is gitignored (source ontology + generated artifacts, all regenerable):

- `data/staging/RadLex.owl` — source ontology (must be supplied locally; not checked in).
- `data/staging/ct-3733*.txt` — sample radiology report used as test input.
- `data/intermediate/radlex_triples.parquet` — output of the OWL ingest step.
- `data/intermediate/radlex.duckdb` — persisted knowledge graph (`nodes`/`edges`/
  `search_docs` tables plus the full-text index).
- `data/output/candidates.jsonl` — candidate new concepts proposed by the agent. Records
  are validated against the graph before being appended: parent/target RIDs must exist and
  relation types must be ones RadLex uses.

The test fixture under `tests/data/` is committed rather than gitignored — it is a ~4,000
concept Parquet subset, so the regression suite runs on a fresh clone without a 52 MB
ontology download.

## Setup

Requires Python 3.13+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
```

Place the RadLex OWL export at `data/staging/RadLex.owl` before running the pipeline.

The graph build installs DuckDB's `fts` extension, which is fetched from the network the
first time and cached in `~/.duckdb` thereafter. On a machine that has never installed it
and has no network, the build fails at that step; search then falls back to exact matching
only, with reduced recall and a logged warning.

## Usage

### 1. Parse the OWL file into a triples table

```python
from pathlib import Path
from res_radlex_parsing.owl_ingest.parse import RadLexOwlParser

RadLexOwlParser(Path("data/staging/RadLex.owl")).load().parse().save(
    Path("data/intermediate/radlex_triples.parquet")
)
```

### 2. Build and persist the knowledge graph

```python
from pathlib import Path
from res_radlex_parsing.graph.build_graph import RadLexGraphBuilder

with RadLexGraphBuilder(
    Path("data/intermediate/radlex_triples.parquet"),
    Path("data/intermediate/radlex.duckdb"),
) as builder:
    builder.load().build().save()
```

### 3. Query the graph

```python
from pathlib import Path
from res_radlex_parsing.graph.query import RadLexGraphQuery

with RadLexGraphQuery(Path("data/intermediate/radlex.duckdb")).load() as query:
    matches = query.search("pulmonary nodule")
    node = query.get_node("RID1327")
    parents = query.get_parents("RID1327")
```

### 4. CLI tools (used by the Pi extension, also runnable directly)

These run inside the project environment. The Claude skill's helper
(`.claude/skills/radlex-concepts/scripts/radlex_kg.py`) instead declares its dependencies
inline (PEP 723) and is invoked as `uv run <script>`, so it works from any directory
without a synced checkout.

```bash
uv run python -m res_radlex_parsing.extraction.tools search --text "pulmonary nodule"
uv run python -m res_radlex_parsing.extraction.tools get-concept --rid RID1327
uv run python -m res_radlex_parsing.extraction.tools propose-concept \
    --name "new finding" --parent-rid RID1327 --rationale "not currently modeled"
```

### 5. Interactive notebook

```bash
uv run marimo edit notebooks/test_owl_ingest.py
```

## Development

```bash
uv run --frozen pytest          # tests (run against a committed fixture graph, and
                                #        against data/intermediate/radlex.duckdb if built)
uv run python tests/eval_search.py   # search-quality comparison across ranking arms
uv run python tests/data/build_fixture.py   # regenerate the committed test fixture
uv run --frozen ruff format .   # format
uv run --frozen ruff check .    # lint
uv run --frozen ty check        # type-check
```

See `CLAUDE.md` for full contribution/style guidelines and `docs/plans/` for design
context.
