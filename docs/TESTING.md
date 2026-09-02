# Testing RadLex.owl

RadLex is tested for logical and structural integrity using
[ROBOT](https://robot.obolibrary.org/), a command-line tool for working with
OWL ontologies. These checks catch problems like inconsistent logic,
accidental duplicate/merged terms, and other curation mistakes before they
land in `RadLex.owl`.

## Continuous integration

Every push to any branch triggers the **ROBOT integrity checks** GitHub
Actions workflow, defined in
[`.github/workflows/robot-integrity.yml`](../.github/workflows/robot-integrity.yml).
The workflow:

1. Installs ROBOT.
2. Runs a reasoner-based consistency check (`tests/scripts/robot-check.sh`).
3. Runs SPARQL-query-based checks (`tests/scripts/robot-report-tests.sh`).

If either check fails, the workflow run is marked failed and the relevant
output is uploaded as a build artifact:

- `robot-unsatisfiable-explanation` — a minimal explanation of why the
  ontology is logically inconsistent or incoherent, if the reasoner check
  fails.
- `robot-report`: The `robot-report.tsv` violations report, if the
  SPARQL-query-based checks fail.

To download an artifact from a failed run, open the run on GitHub and scroll
to the **Artifacts** section at the bottom of the summary page (or use
`gh run download <run-id>`).

## Running the tests locally

All the scripts below live in `tests/scripts/` and are meant to be run from
the repository root.

### 1. Install ROBOT

```sh
tests/scripts/install-robot.sh
```

This downloads the pinned ROBOT version and verifies it against a pinned
checksum, installing it to `tests/scripts/.robot/`. The script prints the
`export PATH=...` line you need; run it (or add it to your shell profile) so
that plain `robot` commands resolve to this install:

```sh
export PATH="$PWD/tests/scripts/.robot:$PATH"
```

You only need to re-run `install-robot.sh` when the pinned `ROBOT_VERSION`
changes — it's a no-op if the correct version is already installed.

### 2. Run the reasoner-based consistency check

```sh
tests/scripts/robot-check.sh
```

This runs the ELK reasoner over `RadLex.owl` and fails if the ontology is
logically inconsistent, has unsatisfiable classes, or if the reasoner infers
equivalences between classes that weren't explicitly asserted (a common
symptom of accidentally duplicated or merged terms). On failure, see
`unsatisfiable-explanation.owl` for details.

### 3. Run the SPARQL-query-based checks

```sh
tests/scripts/robot-report-tests.sh
```

This runs `robot report` using the queries and severity levels listed in
[`tests/robot-report-profile.txt`](../tests/robot-report-profile.txt), and
writes the full results to `robot-report.tsv`. Open that file to see exactly
which terms triggered which violation.

### Adding a new SPARQL check

1. **Add the query file.** Create a new `.rq` SPARQL query file under
   `tests/sparql/robot/`, e.g. `tests/sparql/robot/my_new_check.rq`.

2. **Bind exactly three variables.** `robot report` 
   ([documentation](https://robot.obolibrary.org/report.html)) requires every custom
   query to be a `SELECT` that returns exactly `?entity`, `?property`, and
   `?value` - no more, no fewer:
   - `?entity`: The offending entity (e.g. a class or annotation subject).
     If `?entity` is unbound for a row, that row can't be reported.
   - `?property`: The property involved in the violation (e.g.
     `rdfs:label`).
   - `?value`: The value that's causing the violation (e.g. the malformed
     string).

   A row returned by the query is a violation; a query that returns no rows
   means no violations. See
   [`tests/sparql/robot/leading_trailing_multi_whitespace.rq`](../tests/sparql/robot/leading_trailing_multi_whitespace.rq)
   for a working example.

3. **Reference it from the profile.** Add a line to
   [`tests/robot-report-profile.txt`](../tests/robot-report-profile.txt) with
   the severity level, a tab, then `file:` followed by the query's path
   relative to the repo root:

   ```
   ERROR	file:./tests/sparql/robot/my_new_check.rq
   ```

   Severity is one of `ERROR`, `WARN`, or `INFO`. `ERROR`-level violations
   fail the check (and therefore the CI job); `WARN`/`INFO` are reported but
   don't fail it.

4. **Run it locally** with `tests/scripts/robot-report-tests.sh` to confirm
   the check behaves as expected — check `robot-report.tsv` for the results —
   before pushing.
