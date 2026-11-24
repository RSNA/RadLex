# Anatomic Locations: new classes

Draft for review. `new-classes.tsv` is a [ROBOT template](https://robot.obolibrary.org/template) that adds to RadLex the 965 entries of the [Anatomic Locations Index](https://anatomiclocations.org) (release 1.0.1) that RadLex doesn't have yet. Most are left and right versions of classes RadLex has only unsided.

This branch holds the table only. `RadLex.owl` is not changed yet; once the table is reviewed, it will be applied with ROBOT and the result opened as a pull request.

This is the first step of the Anatomic Locations work. It adds the classes and what belongs to each class itself. Containment and part-whole relationships, and changes to the Anatomic Locations entries RadLex already has, will follow separately.

## Files

| File | What it is |
|---|---|
| `new-classes.tsv` | The ROBOT template: one row per new class. |
| `already-in-radlex.tsv` | Index entries left out of the template because RadLex already has the class under its own RID. Not ROBOT input. |
| `jeff-review.md` | Jeff's review of the first draft of the template (commit 8b45da3). Its RIDs are that draft's; the template has since been renumbered. |
| `proposed-definitions.tsv` | Definitions drafted during that review. Not applied yet. |

## Reading the template

Row 1 is the column name and row 2 is the ROBOT template string. The `ALI ID` and `Parent label` columns have an empty row 2: they are there for reviewers, and ROBOT ignores them. A `|` separates several values in one cell.

## What each new class gets

- A label and a `RID:RadLexID`. RIDs run from `RID51000` to `RID51964`. The range is provisional.
- One or more parent classes (see below).
- Its synonyms as `oboInOwl:hasExactSynonym`, 426 in all.
- A `RID:ExternalRefID` of `ANAT_LOC:` followed by its ID in the Anatomic Locations Index, such as `ANAT_LOC:RID294_RID5824`. The index names these entries by combining two or more RIDs; this links the new RID back to that ID.
- Its other codes as `RID:ExternalRefID`: 854 classes have an FMA code, 551 SNOMED CT, 75 UMLS, and 3 TA2. 88 classes have no code besides the `ANAT_LOC:` one.
- `RID:Radlex_version_of_class_change` of `4.4 new`, and `RID:Source` of `Anatomic Locations Index 1.0.1`.

### Parents

- 828 classes go under their unsided class: left uterine adnexa under `RID294` uterine adnexa.
- 121 go under the part of the combined ID that names the same kind of structure: "first metatarsal" goes under metatarsal, not great toe. Each sided tooth goes under its tooth type and under `RID9131` deciduous tooth or `RID9132` permanent tooth.
- 16 parents were chosen by hand: the twelve numbered ribs under `RID2471` rib, the cranial cavity under `RID32949` anatomical compartment space, the interphalangeal joint of great toe under `RID34532` interphalangeal joint of toe, and the supratentorial and infratentorial brain under `RID13853` segment of brain.
- 142 parents are themselves new classes in this table.

## Changes since the first draft

These follow `jeff-review.md`.

- **48 rows removed.** RadLex already has these classes under another RID, so the table would have duplicated them. They are listed in `already-in-radlex.tsv`, with the index's ID beside the existing RID:
  - 44 share an FMA code with an existing left or right class, such as "left head of femur" and `RID42283` head of left femur (review 1.2).
  - 2 are the left and right head of fibula. RadLex's `RID39763` and `RID39762`, proximal epiphysis of left and right fibula, are its only sided classes under `RID2872` head of fibula, and FMA gives "Head of left fibula" as another name for the proximal epiphysis.
  - 2 are held back: the left and right P3 segment of posterior cerebral artery. RadLex puts the left and right lateral occipital artery under P3 segment and treats the two names as synonyms; the index lists both. They stay out until that is settled.
- **Three parent errors fixed** (review 2.2 and 2.3): cranial cavity, interphalangeal joint of great toe, and permanent tooth as a second parent on the 32 permanent teeth.
- **22 FMA codes added** from review 1.3, each checked against FMA 5.1.0: the anterior tibiotalar, tibionavicular and tibiocalcaneal ligaments, the deep and superficial posterior compartments of leg, the C3/C4 to C7/T1 and L1/L2 to L5/S1 disks, and the supratentorial and infratentorial brain.
- The RIDs were renumbered after the rows were removed.

`already-in-radlex.tsv` also lists 8 entries the first draft had already left out because their name matches an existing class.

## Still open

Left for a later pass; none of it changes which classes are added.

- **Definitions.** None are given. `proposed-definitions.tsv` needs review first.
- **Synonyms** the review calls inexact or ambiguous (3.2), and the tooth-number synonyms (3.3). They are as the index has them.
- **Other FMA codes from the review** where the match needs a decision: wrist joint, common femoral artery, deep posterior tibiotalar ligament.
- **The eight sided brain regions**, such as left frontal brain region, stay in. A brain region is not a lobe.
- **RID range.** `RID51000` onward is a placeholder; the highest RID in use is `RID50859`.
- **New code prefixes.** `ANAT_LOC`, `SNOMEDCT`, and `TA2` are not used in `RID:ExternalRefID` today; `FMA` and `UMLS` are.
- **No `oboInOwl:created_by` or `oboInOwl:creation_date`.**

## Not included

- `Contained_In` and `Part_Of`.
- Any change to an existing class.
- The index's sex-specific flag.
- SNOMED CT expressions that say "left" or "right" of an unsided concept, such as `27175001:272741003=24028007`. Only plain codes are given.

## Applying

With ROBOT on your PATH (see [CONTRIBUTING.md](../../docs/CONTRIBUTING.md#4-run-the-integrity-checks)), from the repository root:

```sh
mkdir -p tmp
robot template --input RadLex.owl --prefix "RID: http://www.radlex.org/RID/" \
  --template templates/anatomic-locations/new-classes.tsv --output tmp/new-classes.owl
robot merge --input RadLex.owl --input tmp/new-classes.owl --output tmp/RadLex.new.owl
```

Applied this way to `main` at 677eba9 with ROBOT 1.9.10, the result has 965 more classes and passes `robot-check.sh` and `robot-report-tests.sh`.

## Source

The tables are generated from the index's data file by `scripts/build_radlex_templates.py` on the `radlex-robot-templates` branch of [talkasab/anatomiclocations.org](https://github.com/talkasab/anatomiclocations.org). Change them there, not by hand.
