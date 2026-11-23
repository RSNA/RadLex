# Anatomic Locations: new classes

Draft for review. `new-classes.tsv` is a [ROBOT template](https://robot.obolibrary.org/template) that adds to RadLex the 1,013 entries of the [Anatomic Locations Index](https://anatomiclocations.org) (release 1.0.1) that RadLex doesn't have yet. Most are left and right versions of classes RadLex has only unsided.

This branch holds the table only. `RadLex.owl` is not changed yet; once the table is reviewed, it will be applied with ROBOT and the result opened as a pull request.

This is the first step of the Anatomic Locations work. It adds the classes and what belongs to each class itself. Containment and part-whole relationships, and changes to the 1,880 Anatomic Locations entries RadLex already has, will follow separately.

## Reading the table

Row 1 is the column name and row 2 is the ROBOT template string. The `ALI ID` and `Parent label` columns have an empty row 2: they are there for reviewers, and ROBOT ignores them. A `|` separates several values in one cell.

## What each new class gets

- A label and a `RID:RadLexID`. RIDs run from `RID51000` to `RID52012`. The range is provisional.
- One or more parent classes (see below).
- Its synonyms as `oboInOwl:hasExactSynonym`, 432 in all.
- A `RID:ExternalRefID` of `ANAT_LOC:` followed by its ID in the Anatomic Locations Index, such as `ANAT_LOC:RID294_RID5824`. The index names these entries by combining two RIDs; this links the new RID back to that ID.
- Its other codes as `RID:ExternalRefID`: 878 classes have an FMA code, 569 SNOMED CT, 75 UMLS, and 3 TA2. 100 classes have no code besides the `ANAT_LOC:` one.
- `RID:Radlex_version_of_class_change` of `4.4 new`, and `RID:Source` of `Anatomic Locations Index 1.0.1`.

### Parents

- 876 classes go under their unsided class: left uterine adnexa under `RID294` uterine adnexa.
- 122 go under the part of the combined ID that names the same kind of structure: "first metatarsal" goes under metatarsal, not great toe. A deciduous incisor goes under both incisor tooth and deciduous tooth.
- 15 parents were chosen by hand: the twelve numbered ribs under `RID28591` rib, the cranial cavity under `RID32952` body cavity subdivision, and the supratentorial and infratentorial brain under `RID13853` segment of brain.
- 142 parents are themselves new classes in this table.

## For reviewers to decide

- **RID range.** `RID51000` onward is a placeholder; the highest RID in use is `RID50784`.
- **New code prefixes.** `ANAT_LOC`, `SNOMEDCT`, and `TA2` are not used in `RID:ExternalRefID` today; `FMA` and `UMLS` are.
- **No definitions.** The contributing guide asks for a definition on each new class. The index has none for these entries, so none are given.
- **No `oboInOwl:created_by` or `oboInOwl:creation_date`.** These can be added as columns once we agree on the values.
- **The hand-picked parents** listed above.

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

Applied this way to `main` at e35d2dc with ROBOT 1.9.10, the result has 1,013 more classes and passes `robot-check.sh` and `robot-report-tests.sh`.

## Source

The table is generated from the index's data file by `scripts/build_radlex_templates.py` on the `radlex-robot-templates` branch of [talkasab/anatomiclocations.org](https://github.com/talkasab/anatomiclocations.org). Change the table there, not by hand.
