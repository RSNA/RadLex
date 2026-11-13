# Contributing to RadLex

**Repository:** [https://github.com/RSNA/RadLex](https://github.com/RSNA/RadLex)  
**Ontology:** [radlex.org](https://radlex.org/)  
**Review Team:** RadLex Curators

## Overview

RadLex is a unified ontology for radiology, developed and maintained by the Radiological Society of North America (RSNA). Contributions are welcome from the radiology and informatics communities. All proposed changes are submitted as GitHub pull requests (PRs) and reviewed for approval by the RadLex Curators team.

## Setup

### Prerequisites

Before contributing, ensure you have the following installed:

| Tool | Purpose | Download |
| ----- | ----- | ----- |
| **Git** | Version control via a terminal | [git-scm.com](https://git-scm.com/) |
| **GitHub Desktop** *(optional)* | Graphical app for Git and GitHub, for contributors who prefer it to the terminal. It can clone or fork the repository, create branches, show what changed in your working copy, commit, push, and open a pull request. This guide gives terminal commands, but each step has a GitHub Desktop equivalent | [Download](https://desktop.github.com/download/); [GitHub Desktop documentation](https://docs.github.com/en/desktop) (installing, setting up, and using it) |
| **Desktop Protégé** (v5.x) | OWL ontology editor | [protege.stanford.edu](https://protege.stanford.edu/) |
| **Java** (11 or later; CI uses 21) | To run ROBOT. Check with `java -version`; macOS and Linux may already have it | [Eclipse Temurin install guide](https://adoptium.net/installation/) (installers and package managers for each platform) |
| **[ROBOT](https://robot.obolibrary.org/)** | Command-line tool for running the integrity checks and generating diffs *(recommended)* | Install the pinned version with `tests/scripts/install-robot.sh` (see [step 4](#4-run-the-integrity-checks)); docs at [robot.obolibrary.org](https://robot.obolibrary.org/) |

### Viewing Ontology Changes in Git *(Optional)*

Protégé can reorder large parts of `RadLex.owl` when it saves, so an ordinary `git diff` of the file is often long and hard to read. You can instead have git show changes to `.owl` and `.ofn` files as a ROBOT diff, listing the axioms and annotations added and removed for each class: the same output as [step 5](#5-generate-a-diff-with-robot-recommended).

The repository's `.gitattributes` file assigns those files to a diff driver named `owl`. Until you configure that driver, git ignores the assignment and shows ordinary text diffs, so this setup is entirely optional. To configure it:

1. **Put ROBOT on your PATH** (see [step 4](#4-run-the-integrity-checks)). Git runs the driver in a separate process, so `robot` must resolve wherever you run `git`, e.g. by adding the `export PATH=...` line to your shell profile.

2. **Save this script** as `robot-git-diff` in a directory on your PATH (e.g. `~/bin/robot-git-diff`), and make it executable (`chmod +x ~/bin/robot-git-diff`):

   ```sh
   #!/bin/sh
   # Git external diff driver: show a ROBOT diff of two OWL files instead of a line diff.
   # Git calls it with 7 arguments: path old-file old-hex old-mode new-file new-hex new-mode
   echo "DIFFERENCES in $1:"
   # Piping through cat makes the script exit 0 even if ROBOT fails (e.g. on a file with merge-conflict
   # markers). Otherwise git stops the whole diff at that file, without showing the remaining files.
   robot diff --left "$2" --right "$5" --format markdown | cat
   ```

3. **Tell git to use it** in your clone of this repository:

   ```sh
   git config diff.owl.command robot-git-diff
   ```

   This setting lives in your clone's `.git/config`; git never commits or shares it.

Once it's configured:

* `git diff` uses the driver automatically. Diffing `RadLex.owl` takes several seconds and about 1.5 GB of memory, since ROBOT loads both versions of the file.
* `git log -p` and `git show` use it only when you add `--ext-diff`, e.g. `git show --ext-diff HEAD`.
* To see the ordinary text diff instead, add `--no-ext-diff`. Summary options such as `git diff --stat` are unaffected.
* GitHub's web view and most IDE diff views don't use git's diff drivers, so they still show text diffs.

## Contribution Workflow

### 1. Fork and Clone the Repository

> **If you have write access to `RSNA/RadLex`**, you don't need a fork: clone `https://github.com/RSNA/RadLex.git` directly and push your branches there. In that clone, `origin` is the RSNA repository, so skip adding `upstream` below, and wherever this guide says `upstream`, use `origin` instead.

Otherwise, fork the repository on GitHub, then clone your fork locally:

```sh
git clone https://github.com/<your-username>/RadLex.git
cd RadLex
```

In your clone, `origin` refers to your fork. Add the RSNA repository as a second remote, named `upstream`, so you can stay in sync with it:

```sh
git remote add upstream https://github.com/RSNA/RadLex.git
```

Ensure you are on the `main` branch, and that it's up-to-date with respect to the RSNA GitHub repository:

```sh
git checkout main
git pull upstream main
```

### 2. Create a Working Branch

Create a descriptively named branch for your changes:

```sh
git checkout -b add-term-pulmonary-nodule
```

Use a short, lowercase, hyphen-separated name that reflects the nature of your edit (e.g., `fix-synonym-liver`, `deprecate-obsolete-terms`, `add-cardiac-terms`).

### 3. Edit the Ontology in Protégé

Open the ontology file (`.owl`) in Protégé and make your changes. Common contribution types include:

* **New terms** — add a class with the required annotations; see [Adding a Class](#adding-a-class)  
* **Corrections** — fix definitions, labels, or logical axioms  
* **Obsoletions** — retire a term without deleting it; see [Obsoleting a Class](#obsoleting-a-class)  
* **Synonym additions** — add `hasExactSynonym` or `RID:Acronym` annotations

> **Tip:** Follow existing term patterns for consistency. Review nearby terms before adding new ones to avoid duplicates.

Save the file from Protégé when done. Avoid making unrelated edits in the same branch.

### 4. Run the Integrity Checks

Every push and PR runs the **ROBOT integrity checks** in CI, and a PR can't be merged until they pass. To catch issues sooner, you can run the same checks locally first, from the repository root:

One-time ROBOT setup:
```sh
tests/scripts/install-robot.sh                  # installs the pinned ROBOT version; no-op if already installed
export PATH="$PWD/tests/scripts/.robot:$PATH"   # so that `robot` resolves to that install
```

Run checks:
```sh
tests/scripts/robot-check.sh                    # reasoner-based consistency check
tests/scripts/robot-report-tests.sh             # SPARQL-query-based checks
```

If `robot-check.sh` fails, see `unsatisfiable-explanation.owl` for why. If `robot-report-tests.sh` fails, `robot-report.tsv` lists each violation and the term that caused it. [TESTING.md](TESTING.md) explains each check, and how to read and fix its failures.

### 5. Generate a Diff with ROBOT *(Recommended)*

Providing a diff file helps reviewers quickly understand the scope of your changes. With ROBOT on your PATH (see [step 4](#4-run-the-integrity-checks)), run this from the repository root. It compares your working copy of `RadLex.owl` against the version on your local `main` branch, and writes the diff to `docs/changes/`, in a file named after your branch (e.g. `docs/changes/add-term-pulmonary-nodule.md`):

```sh
mkdir -p docs/changes tmp
git show main:RadLex.owl > tmp/RadLex-main.owl   # main's version of the file (git ignores tmp/)
robot diff \
  --left tmp/RadLex-main.owl \
  --right RadLex.owl \
  --output "docs/changes/$(git branch --show-current).md" \
  --format markdown
```

> `--format markdown` produces a diff that renders readably on GitHub. Omit it to get ROBOT's default plain-text format.

Before running it, make sure your local `main` is up to date with RSNA's (see [step 1](#1-fork-and-clone-the-repository)) and your branch is rebased onto it (see [step 8](#8-respond-to-review-and-keep-your-branch-up-to-date)). Otherwise the diff will also show changes made on `main` since your branch started, as if your branch had reverted them.

Include the diff in your PR in one of two ways:
 - **If the diff is short**, paste its contents into the **ROBOT diff** section of the PR description, and don't commit the file.
 - **If the diff is long**, commit the file (see step 6), and link to it from the **ROBOT diff** section of the PR description.

To see ROBOT diffs locally whenever you run `git diff`, see [Viewing Ontology Changes in Git](#viewing-ontology-changes-in-git-optional).

### 6. Commit and Push

Stage and commit your changes with a clear, descriptive message:

```sh
git add RadLex.owl
git add docs/changes/add-term-pulmonary-nodule.md   # only if you are committing the diff (see step 5)
git commit -m "Add term: pulmonary nodule (RID12345) with parent lung lesion"
```

Push the branch to `origin` (your fork, or `RSNA/RadLex` if you have write access):

```sh
git push origin add-term-pulmonary-nodule
```

### 7. Open a Pull Request

1. Navigate to [github.com/RSNA/RadLex](https://github.com/RSNA/RadLex) and click **Compare & pull request**.  
2. Set the base branch to `main`.  
3. Fill in the [pull request template](../.github/PULL_REQUEST_TEMPLATE.md), which GitHub pre-fills in the description box:  
   * **Fixes** — the issue this PR resolves, if any (e.g. `Fixes #42`); delete the line otherwise  
   * **Summary** — one or two sentences on what the PR changes  
   * **Details** *(optional)* — modelling choices, alternatives considered, open questions  
   * **Motivation** — why the change is needed, citing sources (ACR guidance, literature, etc.) where they apply  
   * **Affected classes and properties** — what was added, changed, or obsoleted, listed by RID and label (or by property name); a group with more than 25 entries can be summarised with a description and a count  
4. If you generated a ROBOT diff (see [step 5](#5-generate-a-diff-with-robot-recommended)), paste it into the template's **ROBOT diff** section, or link to it there if you committed it under `docs/changes/`; otherwise delete that section.  
5. Submit the pull request.

Before it can be merged, your PR must meet the [Merge Requirements](#merge-requirements).

### 8. Respond to Review and Keep Your Branch Up to Date

While your PR is open:

* **Address review comments** by committing further changes to the same branch and pushing them; the PR updates automatically. After each change to `RadLex.owl`, re-run the integrity checks ([step 4](#4-run-the-integrity-checks)) and regenerate the ROBOT diff ([step 5](#5-generate-a-diff-with-robot-recommended)).
* **Keep your branch up to date with `main`.** A PR can't be merged until its branch includes everything on RSNA's `main` (see [Merge Requirements](#merge-requirements)). If `main` has moved on since you created your branch, rebase the branch onto it (with `upstream` set up as in [step 1](#1-fork-and-clone-the-repository)):

  ```sh
  git fetch upstream
  git rebase upstream/main
  git push --force-with-lease origin <your-branch>
  ```

  Rebasing rewrites the branch's commits, so the push must be forced; `--force-with-lease` refuses to overwrite commits on the remote branch that you haven't fetched. We prefer rebasing to merging `main` into your branch. GitHub's **Update branch** button is turned off for this repository, so update the branch locally as above.

## Editing Conventions

How to make common kinds of edits to `RadLex.owl`.

### Adding a Class

Give each new class:

* an IRI of the form `http://www.radlex.org/RID/RIDnnnnn`, with the same `RIDnnnnn` as its `RID:RadLexID` value
* a preferred name as an English `rdfs:label` (language tag `en`)
* a parent class, via `rdfs:subClassOf`
* a definition, as `obo:IAO_0000115` (definition), with its source in `RID:Source`
* any synonyms (see **Synonym additions** in [step 3](#3-edit-the-ontology-in-protégé))
* `RID:Radlex_version_of_class_change` set to the release that introduces it, e.g. `4.4 new`, and `oboInOwl:created_by` / `oboInOwl:creation_date`, as recently added terms have

### Obsoleting a Class

RadLex never deletes a class or reuses its RID. When a term should no longer be used (for example, it duplicates another term or is erroneous), it is *obsoleted*: moved under `RID15849` ("Obsolete RadLex Term"), which tools and the CI checks treat as retired. RadLex does not use `owl:deprecated`.

A term that is merely *medically* outdated is not necessarily a candidate: it may be kept as a live term, with an `RID:Comment` noting its status.

To obsolete a class:

1. **Replace its parents.** Remove its existing `rdfs:subClassOf` parents and all of its logical axioms (e.g. `some` restrictions), and make it a direct subclass of `RID15849`.
2. **Keep its identity.** Leave its IRI and `RID:RadLexID` unchanged.
3. **Record its name.** Add `RID:Preferred_Name_for_Obsolete` with the term's preferred name, and keep its `rdfs:label` value(s). CI fails if an obsolete class has no English label.
4. **Point to its replacement**, if there is one: add `RID:Replaced_by`, referencing the live class to use instead.
5. **Explain why**, in an `RID:Comment` (e.g. "duplicate of RIDnnnnn").
6. **Handle its subclasses.** Every subclass of an obsolete class is itself obsolete. Before obsoleting a class, re-parent any subclasses that should stay live.
7. **Re-point references.** Any live class whose axioms name the obsoleted class must be updated to name its replacement instead; CI fails otherwise. In Protégé, the class's **Usage** view lists these references.

Some obsolete classes also carry `RID:Radlex_version_of_class_change` with the release that obsoleted them, e.g. `4.4 obs`.

In your PR, list each obsoleted class under **Obsoleted** in the template.

### Guidelines for Good Contributions

* **One logical change per pull request.** Avoid bundling unrelated edits.  
* **Include definitions.** New terms should have a clear, source-referenced textual definition.  
* **Cite sources.** Link to authoritative references (e.g., ACR guidelines, peer-reviewed literature) where applicable.  
* **Check for existing terms.** Search RadLex at [radlex.org](https://radlex.org/) before adding a new term.  
* **Preserve ontology hygiene.** Do not remove or alter IRIs of existing terms; obsolete them instead (see [Obsoleting a Class](#obsoleting-a-class)).

## Repository Policies

How changes reach `main`, and how releases are made.

### Merge Requirements

`main` is protected by a GitHub ruleset that applies to everyone, including repository admins:

1. **All changes go through a PR.** Nobody can push to `main` directly, force-push to it, or delete it.
2. **The PR's branch must be up to date with `main`.** If `main` has moved on since the branch was created, rebase the branch (see [step 8](#8-respond-to-review-and-keep-your-branch-up-to-date)).
3. **The PR must be approved** by at least one repository editor who is not its author.
4. **The ROBOT integrity checks must pass.** The `robot-integrity` CI job runs on every push and PR (see [step 4](#4-run-the-integrity-checks) and [TESTING.md](TESTING.md)).
5. **Merges keep `main`'s history linear.** A PR is merged with **Squash and merge** or **Rebase and merge**; **Create a merge commit** is not allowed. After the merge, GitHub deletes the PR's branch automatically.

### Review Process

Pull requests are reviewed by the **RadLex Curators** team. Reviewers may:

* Approve and merge the contribution as submitted  
* Request clarifications or modifications before merging  
* Close contributions that fall outside the scope of RadLex

Please respond promptly to reviewer comments. Contributions that remain unaddressed for an extended period may be closed and can be resubmitted.

### Versioning

Releases are given a version number of the form MAJOR.MINOR, e.g. `4.3`:  
   1. "Breaking" (incompatible) changes get a new major version-number (e.g., for 4.3, the major-version is "4").  
   2. All other changes get a new minor number.

### Releases

Releases are made from the `main` branch:  
   1. **Push a git tag** against the `main` branch. The tag should be just the version number, e.g. `4.4`.  
   2. **Create a Release** against that tag. In GitHub, that is done at [https://github.com/RSNA/RadLex/releases/new](https://github.com/RSNA/RadLex/releases/new). (creation of the tag can be simultaneous with the release-creation, in that interface)

## Questions and Discussions

For questions about the contribution process or RadLex scope, open a [GitHub Issue](https://github.com/RSNA/RadLex/issues) or contact the RadLex Curators through the RSNA website.

## To-Do

* Establish RadLex ID "ranges" for different contributors, to allow for work on multiple PRs simultaneously.
* Add a "Configuring Protégé" section, covering for example:
  * giving Protégé enough memory (Java heap) to open the ~50 MB `RadLex.owl`
  * showing classes by their `rdfs:label` rather than their RID
  * new-entity settings, so that new classes get RID-style IRIs
  * saving in RDF/XML, the file's current format, and checking `git diff --stat` afterwards for unexpected re-serialisation churn
* Decide whether to adopt [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH) for releases, and if so, define what counts as a "breaking" change to the ontology.
* Determine preferred contact methods for the RadLex Curators and the RadLex chair, then update [Questions and Discussions](#questions-and-discussions):
  * RSNA's [RadLex page](https://www.rsna.org/practice-tools/data-tools-and-standards/radlex-radiology-lexicon) lists two feedback addresses: `radlexfeedback@lists.rsna.org` (term comments and suggestions) and `radlex-feedback@lists.rsna.org` (Playbook questions). Does either reach the curators or the chair? Which spelling is correct, and should they be merged?
  * Is that list the address to publish for contribution questions?
  * Should the repository have its own route, such as enabling GitHub Discussions, or adding a `SUPPORT.md` (which GitHub links from the new-issue page)?
