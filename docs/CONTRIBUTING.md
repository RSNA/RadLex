# **Contributing to RadLex**

**Repository:** [https://github.com/RSNA/RadLex](https://github.com/RSNA/RadLex)  
**Ontology:** [radlex.org](https://radlex.org/)  
**Review Team:** RadLex Curators

---

## **Overview**

RadLex is a unified ontology for radiology, developed and maintained by the Radiological Society of North America (RSNA). Contributions are welcome from the radiology and informatics communities. All proposed changes are submitted as GitHub pull requests (PRs) and reviewed for approval by the RadLex Curators team.

---

## **Prerequisites**

Before contributing, ensure you have the following installed:

| Tool | Purpose | Download |
| ----- | ----- | ----- |
| **Git** | Version control via a terminal | [git-scm.com](https://git-scm.com/) |
| **GitHub Desktop** | Desktop version | [https://desktop.github.com/download/](https://desktop.github.com/download/) |
| **Desktop Protégé** (v5.x) | OWL ontology editor | [protege.stanford.edu](https://protege.stanford.edu/) |
| **ROBOT** | Command-line tool for ontology diff generation and other manipulation/testing *(recommended)* | [robot.obolibrary.org](http://robot.obolibrary.org/) |

---

## Conventions

In the RadLex git repository, we adhere to the following conventions:

### Versioning
Releases are given a version number based on the general convention of [Semantic Versions](https://semver.org/), in the form x.y(.z):   
   1. "Breaking" (incompatible) changes get a new major version-number (e.g., for 4.3, the major-version is "4").   
   2. New features that are backwards-compatible get a new minor number.  
   3. Fixes get a new patchlevel number.

### Releases
Releases are made from the `main` branch:  
   1. **Push a git tag** against the `main` branch. The tag should be just the semantic-version number, e.g. `4.4` (or `4.4.0`).  
   2. **Create a Release** against that tag. In GitHub, that is done at [https://github.com/RSNA/RadLex/releases/new](https://github.com/RSNA/RadLex/releases/new). (creation of the tag can be simultaneous with the release-creation, in that interface)

### Contributing Changes
`main` is protected by a GitHub ruleset that applies to everyone, including repository admins:

1. Contributions are made in branches off of main; when a contribution is ready to be reviewed, create a PR requesting merge of the branch into `main`. Nobody can push to `main` directly, force-push to it, or delete it.

2. Branches must be "up to date" (with respect to `main`) before merging. Note that this may require updating (we prefer rebasing) a branch if other changes to `main` have happened since a given contribution branch was opened. To rebase a branch onto the latest RSNA `main` (with `upstream` set up as in [step 1](#1-fork-and-clone-the-repository)):

   ```sh
   git fetch upstream
   git rebase upstream/main
   git push --force-with-lease origin <your-branch>
   ```

   Rebasing rewrites the branch's commits, so the push must be forced; `--force-with-lease` refuses to overwrite commits on the remote branch that you haven't fetched.

   GitHub's **Update branch** button is turned off for this repository, so update the branch locally as above.

3. Merges to `main` must be approved by at least one repository-editor who is not the PR author.

4. The **ROBOT integrity checks** CI job (`robot-integrity`; see [TESTING.md](TESTING.md)) must pass on the PR.

5. `main` keeps a linear history, so a PR is merged with **Squash and merge** or **Rebase and merge**. **Create a merge commit** is not allowed. After the merge, GitHub deletes the PR's branch automatically.

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

* **New terms** — give each new class:
  * an IRI of the form `http://www.radlex.org/RID/RIDnnnnn`, with the same `RIDnnnnn` as its `RID:RadLexID` value
  * a preferred name as an English `rdfs:label` (language tag `en`)
  * a parent class, via `rdfs:subClassOf`
  * a definition, as `RID:Definition`, with its source in `RID:Source`
  * any synonyms (see **Synonym additions** below)
  * `RID:Radlex_version_of_class_change` set to the release that introduces it, e.g. `4.4 new`, and `oboInOwl:created_by` / `oboInOwl:creation_date`, as recently added terms have
* **Corrections** — fix definitions, labels, or logical axioms  
* **Obsoletions** — retire a term without deleting it; see [Obsoleting a Class](#obsoleting-a-class)  
* **Synonym additions** — add `hasExactSynonym` or `RID:Acronym` annotations

> **Tip:** Follow existing term patterns for consistency. Review nearby terms before adding new ones to avoid duplicates.

Save the file from Protégé when done. Avoid making unrelated edits in the same branch.

### 4. Generate a Diff with ROBOT *(Recommended)*

Providing a diff file helps reviewers quickly understand the scope of your changes. With ROBOT installed and available on your PATH, run this from the repository root. It writes the diff to `docs/changes/`, in a file named after your branch (e.g. `docs/changes/add-term-pulmonary-nodule.md`):

```sh
mkdir -p docs/changes
robot diff \
  --left-iri https://raw.githubusercontent.com/RSNA/RadLex/main/RadLex.owl \
  --right RadLex.owl \
  --output "docs/changes/$(git branch --show-current).md" \
  --format markdown
```

> `--format markdown` produces a diff that renders readably on GitHub. Omit it to get ROBOT's default plain-text format.

Include the diff in your PR in one of two ways:
 - **If the diff is short**, paste its contents into the **ROBOT diff** section of the PR description, and don't commit the file.
 - **If the diff is long**, commit the file (see step 5), and link to it from the **ROBOT diff** section of the PR description.

If you change `RadLex.owl` again after opening the PR (e.g. in response to review), re-run the command above so the diff stays current.

### 5. Commit and Push

Stage and commit your changes with a clear, descriptive message:

```sh
git add RadLex.owl
git add docs/changes/add-term-pulmonary-nodule.md   # only if you are committing the diff (see step 4)
git commit -m "Add term: pulmonary nodule (RID12345) with parent lung lesion"
```

Push the branch to `origin` (your fork, or `RSNA/RadLex` if you have write access):

```sh
git push origin add-term-pulmonary-nodule
```

### 6. Open a Pull Request

1. Navigate to [github.com/RSNA/RadLex](https://github.com/RSNA/RadLex) and click **Compare & pull request**.  
2. Set the base branch to `main`.  
3. Fill in the [pull request template](../.github/PULL_REQUEST_TEMPLATE.md), which GitHub pre-fills in the description box:  
   * **Fixes** — the issue this PR resolves, if any (e.g. `Fixes #42`); delete the line otherwise  
   * **Summary** — one or two sentences on what the PR changes  
   * **Details** *(optional)* — modelling choices, alternatives considered, open questions  
   * **Motivation** — why the change is needed, citing sources (ACR guidance, literature, etc.) where they apply  
   * **Affected classes and properties** — what was added, changed, or obsoleted, listed by RID and label (or by property name); a group with more than 25 entries can be summarised with a description and a count  
4. If you generated a ROBOT diff (see [step 4](#4-generate-a-diff-with-robot-recommended)), paste it into the template's **ROBOT diff** section, or link to it there if you committed it under `docs/changes/`; otherwise delete that section.  
5. Submit the pull request.

---

## Obsoleting a Class

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

---

## Review Process

Pull requests are reviewed by the **RadLex Curators** team. Reviewers may:

* Approve and merge the contribution as submitted  
* Request clarifications or modifications before merging  
* Close contributions that fall outside the scope of RadLex

Please respond promptly to reviewer comments. Contributions that remain unaddressed for an extended period may be closed and can be resubmitted.

---

## Guidelines for Good Contributions

* **One logical change per pull request.** Avoid bundling unrelated edits.  
* **Include definitions.** New terms should have a clear, source-referenced textual definition.  
* **Cite sources.** Link to authoritative references (e.g., ACR guidelines, peer-reviewed literature) where applicable.  
* **Check for existing terms.** Search RadLex at [radlex.org](https://radlex.org/) before adding a new term.  
* **Preserve ontology hygiene.** Do not remove or alter IRIs of existing terms; obsolete them instead (see [Obsoleting a Class](#obsoleting-a-class)).

---

## Questions and Discussions

For questions about the contribution process or RadLex scope, open a [GitHub Issue](https://github.com/RSNA/RadLex/issues) or contact the RadLex Curators through the RSNA website.

## To-Do

* Establish RadLex ID "ranges" for different contributors, to allow for work on multiple PRs simultaneously.

