# Review of `new-classes.tsv`

Review of the draft table on branch `add-anatomic-locations-classes` (commit 8b45da3), started 2026-11-23. No PR is open yet, so findings are logged here.

Sources checked:

- `RadLex.owl` on this branch.
- The index's data file, `data/body_parts.json` (release 1.0.1), on the `radlex-robot-templates` branch of talkasab/anatomiclocations.org.
- FMA 5.1.0 as served by EBI OLS (`https://www.ebi.ac.uk/ols4`), looked up by IRI.
- SNOMED CT International Edition, release 2025-10-17, as served by the same OLS (ontology `snomed`).

UMLS was not checked: it needs a license (applied for). SNOMED International's own browser (snomedbrowser.org) refuses scripted access, so the six SNOMED CT codes OLS can't resolve were checked by hand in that browser, against the US Edition 2026-09-01. All six are correct (1.5).

## 1. Cross-reference IDs

### 1.1 Summary

- The table has no format errors. The `ANAT_LOC` code on every row matches its `ALI ID`. No code appears on more than one row, and every left/right pair has the same set of code systems.
- No code was lost on the way from the index. Every code in `body_parts.json` for these 1,013 entries reaches the table, except the 384 SNOMED CT post-coordinated expressions the README already excludes. The index has MeSH codes (203), but none are on these entries.
- **All 878 FMA codes are valid and correct.** Each one resolves in FMA 5.1.0, none is obsolete, and each FMA label agrees with the class on side and meaning. Some left/right pairs have FMA IDs far apart (the finger phalanges, the ribs, the carotids). I checked those by label, and they are correct.
- **44 FMA codes are already on existing RadLex classes.** These rows are duplicates, not just shared codes. See 1.2, the most serious finding so far.
- 135 rows have no FMA code. I found good FMA candidates for 26 of them (1.3).

### 1.2 Duplicates of existing RadLex classes (blocking)

For 44 rows (22 left/right pairs), RadLex already has the sided class with the same FMA code, usually as a subclass of the same unsided parent. Applying the table would create a second class for the same structure. The generator probably missed them because the existing sided classes aren't tied to the index's combined IDs (for example `RID2700_RID5824`).

| New row | Label | FMA | Existing class | Existing label |
|---|---|---|---|---|
| RID51048 | left head of femur | 55012 | RID42283 | head of left femur |
| RID51049 | right head of femur | 55011 | RID42282 | head of right femur |
| RID51244 | left common peroneal nerve | 45358 | RID28038 | left common fibular nerve |
| RID51245 | right common peroneal nerve | 45357 | RID28037 | right common fibular nerve |
| RID51254 | left vastus medialis muscle | 38933 | RID48221 | left vastus medialis |
| RID51255 | right vastus medialis muscle | 38932 | RID48220 | right vastus medialis |
| RID51256 | left vastus intermedius muscle | 38935 | RID48224 | left vastus intermedius |
| RID51257 | right vastus intermedius muscle | 38934 | RID48223 | right vastus intermedius |
| RID51258 | left vastus lateralis muscle | 38931 | RID48218 | left vastus lateralis |
| RID51259 | right vastus lateralis muscle | 38930 | RID48217 | right vastus lateralis |
| RID51260 | left rectus femoris muscle | 38929 | RID48215 | left rectus femoris |
| RID51261 | right rectus femoris muscle | 38928 | RID48214 | right rectus femoris |
| RID51306 | left greater tuberosity of humerus | 23392 | RID42471 | greater tubercle of left humerus |
| RID51307 | right greater tuberosity of humerus | 23391 | RID42470 | greater tubercle of right humerus |
| RID51308 | left lesser tuberosity of humerus | 23395 | RID43190 | (lesser tubercle of left humerus) |
| RID51309 | right lesser tuberosity of humerus | 23394 | RID43189 | (lesser tubercle of right humerus) |
| RID51310 | left long head of biceps brachii tendon | 65153 | RID41465 | tendon of long head of left biceps brachii |
| RID51311 | right long head of biceps brachii tendon | 65152 | RID41464 | (right counterpart) |
| RID51312 | left short head of biceps brachii tendon | 65155 | RID41467 | (left counterpart) |
| RID51313 | right short head of biceps brachii tendon | 65154 | RID41466 | (right counterpart) |
| RID51318 | left capitellum of humerus | 23375 | RID39786 | (capitulum of left humerus) |
| RID51319 | right capitellum of humerus | 23374 | RID39785 | (capitulum of right humerus) |
| RID51326 | left radial collateral ligament of elbow | 38868 | RID40854 | radial collateral ligament of left elbow joint |
| RID51327 | right radial collateral ligament of elbow | 38867 | RID40853 | (right counterpart) |
| RID51328 | left annular ligament of radius | 38880 | RID40861 | (left counterpart) |
| RID51329 | right annular ligament of radius | 38879 | RID40860 | (right counterpart) |
| RID51330 | left head of radius | 39781 | RID42285 | (head of left radius) |
| RID51331 | right head of radius | 39782 | RID42284 | (head of right radius) |
| RID51332 | left head of ulna | 299868 | RID42288 | (head of left ulna) |
| RID51333 | right head of ulna | 299866 | RID42287 | (head of right ulna) |
| RID51338 | left radial collateral ligament of wrist | 40018 | RID40888 | (left counterpart) |
| RID51339 | right radial collateral ligament of wrist | 40017 | RID40887 | (right counterpart) |
| RID51340 | left ulnar collateral ligament of wrist | 40016 | RID40885 | (left counterpart) |
| RID51341 | right ulnar collateral ligament of wrist | 40015 | RID40884 | (right counterpart) |
| RID51783 | left medial orbitofrontal artery | 50344 | RID36415 | left medial frontobasal artery |
| RID51784 | right medial orbitofrontal artery | 50343 | RID36414 | (right counterpart) |
| RID51793 | left lenticulostriate artery | 50378 | RID36446 | anterolateral central branch of left middle cerebral artery |
| RID51794 | right lenticulostriate artery | 50377 | RID36445 | (right counterpart) |
| RID51795 | left medial lenticulostriate artery | 50432 | RID36448 | (medial striate branch of left MCA) |
| RID51796 | right medial lenticulostriate artery | 50431 | RID36447 | (right counterpart) |
| RID51813 | left medial posterior choroidal artery | 50673 | RID44733 | left posterior medial choroidal artery |
| RID51814 | right medial posterior choroidal artery | 50672 | RID44732 | (right counterpart) |
| RID51815 | left lateral posterior choroidal artery | 50675 | RID44735 | left posterior lateral choroidal artery |
| RID51816 | right lateral posterior choroidal artery | 50674 | RID44734 | (right counterpart) |

Labels in parentheses are paraphrased from the German label or from the left/right counterpart. I didn't read the English label for every row.

**Suggested fix:** drop these 44 rows from the table. Put the index's label and synonyms on the existing classes as synonyms, and the `ANAT_LOC:` and SNOMED CT codes as `RID:ExternalRefID`. That belongs to the separate "changes to existing entries" step. No other row in the table has one of these 44 as its parent, so dropping them breaks nothing in the table.

Two other pairs sit under the same parent as an existing sided class that has a different FMA code. I think these are distinct structures, not duplicates, but a second opinion would help:

- RID51058/RID51059 *left/right head of fibula* (FMA:321500/321499), next to RID39763/RID39762 *proximal epiphysis of left/right fibula* (FMA:33731/33730).
- RID51811/RID51812 *left/right P3 segment of posterior cerebral artery* (no FMA), next to RID44763/RID44762 *left/right lateral occipital artery*.

### 1.3 Rows without an FMA code: candidates found

These 135 rows include all 100 rows whose only code is `ANAT_LOC:`. I searched FMA 5.1.0 by label and synonym, and also tried FMA's own naming patterns.

**Strong matches** (the FMA label names the same structure). I recommend adding these:

| Row(s) | Label | Proposed FMA (left / right) | FMA label |
|---|---|---|---|
| RID51354 / RID51355 | left / right wrist joint | 35299 / 35298 | Left / Right wrist joint |
| RID51096 / RID51097 | left / right anterior tibiotalar ligament | 44069 / 44068 | Anterior tibiotalar part of medial ligament of left / right ankle joint |
| RID51098 / RID51099 | left / right deep posterior tibiotalar ligament | 44071 / 44070 | Posterior tibiotalar part of medial ligament of left / right ankle joint |
| RID51100 / RID51101 | left / right tibionavicular ligament | 44073 / 44072 | Tibionavicular part of medial ligament of left / right ankle joint |
| RID51102 / RID51103 | left / right tibiocalcaneal ligament | 44075 / 44074 | Tibiocalcaneal part of medial ligament of left / right ankle joint |
| RID51032 / RID51033 | left / right deep posterior compartment of leg | 45176 / 45175 | Deep part of posterior compartment of left / right leg |
| RID51034 / RID51035 | left / right superficial posterior compartment of leg | 45182 / 45180 | Superficial part of posterior compartment of left / right leg |
| RID51212 / RID51213 | left / right common femoral artery | 70250 / 70249 | Left / Right femoral artery |
| RID51947 | supratentorial brain | 322211 | Supratentorial region of brain |
| RID51948 | infratentorial brain | 322212 | Infratentorial region of brain |

Notes on these matches:

- **Common femoral artery.** FMA's "femoral artery" is the vessel the term "common femoral" means. But the index gives the unsided `RID958` the code FMA:0323778 "Common femoral artery", a separate class. Whichever you choose, the sided and unsided codes should agree.
- **Infratentorial region.** FMA 5.1 has two classes with this label, `fma322212` and `fma0327741`. I chose the older one.

**Intervertebral disks.** The index gives these disks no FMA code, but FMA has them. FMA names each disk after the vertebra above it, and its synonym gives the interspace:

| Row | Label | Proposed FMA | FMA synonym |
|---|---|---|---|
| RID51483 | C2/C3 cervical intervertebral disk | (not found) | |
| RID51484 | C3/C4 | 13896 | Intervertebral disk, C3-C4 |
| RID51485 | C4/C5 | 13897 | Intervertebral disk, C4-C5 |
| RID51486 | C5/C6 | 13898 | Intervertebral disk, C5-C6 |
| RID51487 | C6/C7 | 13899 | Intervertebral disk, C6-C7 |
| RID51488 | C7/T1 | 13900 | Intervertebral disk, C7-T1 |
| RID51489 | L1/L2 | 16033 | Intervertebral disk, L1-L2 |
| RID51490 | L2/L3 | 16034 | Intervertebral disk, L2-L3 |
| RID51491 | L3/L4 | 16035 | Intervertebral disk, L3-L4 |
| RID51492 | L4/L5 | 16036 | Intervertebral disk, L4-L5 |
| RID51493 | L5/S1 | 16037 | Intervertebral disk, L5-S1 |

Don't use FMA's "C2-C3 intervertebral disk level" classes (`fma0326024` and the others in that series) for these rows. They name the level, not the disk. They fit RadLex's existing level classes (`RID6182` *C2/C3*, and so on, under *cervical intervertebral level*), which belong to the later step.

**Weaker matches.** These need a decision, not a lookup:

- **RID52005–RID52012, left/right frontal/temporal/occipital/parietal brain region.** FMA has the left and right lobes (72970/72969 frontal, 72972/72971 temporal, 72974/72973 parietal, 72976/72975 occipital), but RadLex already has *left frontal lobe* (with FMA:72970) and the others. The unsided *frontal brain region* (`RID6391`) sits under *brain region* (`RID6390`), separate from *frontal lobe*. Either these new classes duplicate the existing sided lobes, or they mean something broader and FMA doesn't fit. Which is it? (This question belongs under parents as much as under codes.)
- **RID51817–RID51820, anterior/posterior thalamoperforating artery.** FMA has only left/right *thalamoperforating artery* (50665/50664), with no anterior/posterior split. That would be a broader match, so I'd leave these rows without FMA.
- **RID51597/RID51598, carotid space.** FMA has left/right *carotid sheath* (57971/57970), which isn't the same thing as the space. I'd leave these without FMA.
- **RID51302/RID51303, glenohumeral ligament.** FMA has sided superior, middle and inferior glenohumeral ligaments (e.g. 35440 "Left superior glenohumeral ligament"), but no sided generic class. I'd leave these without FMA.

**Nothing found in FMA 5.1** (by label, synonym, or the obvious FMA phrasing): adrenal artery (FMA has only superior, middle and inferior suprarenal), accessory breast tissue, calcaneal tuberosity, talar sulcus, superficial femoral artery, lumbricals and interossei of the foot, inguinal/axillary/intramammary/mesorectal lymph node, common extensor tendon, palmar/dorsal radioulnar ligament, scapholunate ligament, capitohamate/capitolunate joint, metacarpal bone, brachial vein, renal calyx, retropharyngeal/perivertebral/intraconal/extraconal space, half of pharyngeal tonsil, fold of incus, ethmoidal infundibulum, uncinate process of ethmoid, the A2/M3/M4/P3 segments, lateral lenticulostriate artery, artery of central sulcus, superior/inferior internal parietal artery, the PICA segments and inferior vermian artery, circumflex pontine artery, and superficial/inferior cerebral vein. For many of these, FMA has only the numbered members or the sided set (for example "First lumbrical of left foot", "Left axillary lymph node group"), not a sided generic class. Leaving them without FMA is reasonable.

### 1.4 Other code issues

- **The FMA format with a leading zero.** FMA classes added in 5.x have IRIs with a leading zero (`fma0323778`). The index writes them without it (`FMA:323778`). That applies to the unsided `RID958`, `RID961`, `RID2068` and `RID2259` codes, not to any code in this table, so it doesn't affect this table. But a lookup by `FMA:323778` fails, so pick one form before the existing-entries step adds these codes.
- **The SNOMED CT prefix.** The README says `SNOMEDCT` is a new prefix. RadLex already has 6 `RID:ExternalRefID` values with the prefix `SNOMED_RT:` (e.g. `RID:ExternalRefID` `SNOMED_RT:62914000`). Some are true SNOMED RT codes (`T-32003`) and some are SNOMED CT IDs. `SNOMEDCT:` is still the better choice, but those 6 should be noted, and maybe fixed later.
- **No SNOMED CT code at all for 60 rows.** 444 rows lack a plain SNOMED CT code: 384 have an expression in the index, which the table drops, and 60 have nothing. Section 1.5 checks whether SNOMED CT now has plain codes for them.
- **TA2 is only partly covered.** Only the first rib (TA2:1107) and second rib (TA2:1111) have TA2 codes. TA2 also lists the eleventh and twelfth ribs separately, so `RID51524` and `RID51527` probably have TA2 codes too. Not verified.
- **Two TA2 codes on one class.** `RID51590` *cranial cavity* has `TA2:100` and `TA2:413`. One of them may name something else, such as the cranial cavity as a whole versus its interior. Check which TA2 entries these are.
- **UMLS.** Only the unsided ribs, the teeth and the disks have UMLS CUIs. The sided ribs (`left first rib` etc.) have none. Not checked against UMLS.

### 1.5 SNOMED CT (checked against OLS)

**The 569 SNOMED CT codes in the table.** 553 resolve, are active, and agree with the row on side and wording. 10 more differ only in wording and are correct: calcaneum for calcaneus, *triangular bone of wrist* for triquetrum, *eye proper* for globe, "cochlear", and *vestibule of inner ear* for *vestibule of bony labyrinth*. No code has the wrong side.

**6 codes are not in the International Edition** as of 2025-10-17, but all six are correct:

| Row(s) | Label | Code(s) | Why OLS lacks them |
|---|---|---|---|
| RID51214 / RID51215 | left / right superficial femoral artery | 640541000146106 / 640551000146109 | National-extension IDs (namespace `1000146`), not International |
| RID51218 / RID51219 | left / right deep femoral artery | 640511000146105 / 640521000146100 | Same |
| RID51284 / RID51285 | left / right inguinal lymph node | 1396723007 / 1396724001 | International IDs, probably newer than the 2025-10-17 release |

**Resolved:** on 2026-11-23, Jeff checked all six by hand in the SNOMED CT browser, in the US Edition 2026-09-01, and found every one correct. They can stay in the table as they are. Some other codes in the table also have extension IDs (34 in namespace `1000087`, 2 in `1000119`), but all of them resolve in the International Edition, so they're fine.

**Rows without a SNOMED CT code: nothing to add.** Of the 384 rows with an expression, none has a matching lateralized concept in the 2025-10-17 International Edition. I looked under each focus concept and its "Entire …" child. The expressions are still the only way to code these rows in SNOMED CT. Text search on the label and synonyms found nothing usable for any of the 444 rows:

- *Left/right common extensor tendon* (1343546001/1343547005) are the tendon's attachment at the elbow (enthesis), not the tendon itself.
- *Structure of ligament of left/right glenohumeral joint* (787935006/787936007) is broader than *glenohumeral ligament*. It would fit as a broader match at most.
- The rest were disorder concepts.

This answers the question the README's "Not included" list leaves open. Dropping the expressions loses the only SNOMED CT coding for 384 rows, and no plain code replaces them. If RadLex wants SNOMED CT for these rows, it would need to store the expressions, perhaps as a separate annotation property, since `RID:ExternalRefID` is a plain code.

### 1.6 How these checks were run

The scripts are in the session scratchpad, not the repo:

1. Parse the `Codes` column. Check the format of each prefix, codes repeated across rows, and left/right symmetry.
2. Compare the codes with every `RID:ExternalRefID` in `RadLex.owl`. This found the duplicates in 1.2.
3. Compare the codes with `body_parts.json`.
4. Look up each FMA code by IRI in OLS (`/api/ontologies/fma/terms?iri=http://purl.org/sig/ont/fma/fma<ID>`). Compare its label's side and wording with the row.
5. For rows without FMA, run an OLS text search on the label and synonyms, then targeted searches using FMA phrasing.
6. Look up each SNOMED CT code by IRI in OLS (`/api/ontologies/snomed/terms?iri=http://snomed.info/id/<SCTID>`) and compare it with the row as in step 4.
7. For rows without a SNOMED CT code, list the children and grandchildren of the expression's focus concept (via the "Entire …" child) and keep those whose label has the row's side. Then run an OLS text search on the label and synonyms.

## 2. Parents

### 2.1 Summary

- **The structure is sound.** All 1,033 parent links (993 rows with one parent, 20 with two) resolve. The 891 that point at existing RadLex classes reach a class that isn't deprecated and sits under *anatomical entity*, and the `Parent label` column matches each one's RadLex label. The other 142 point at classes new in this table.
- **Sided rows follow the index exactly.** Each of the 876 sided rows has as its parent the class that corresponds to the index's own `unsidedId`, and every left/right pair has the same parent. That's RadLex's existing pattern too: for example, RID48221 *left vastus medialis* has a single parent, its unsided class.
- **Two parents are wrong** (2.2), and **one group is missing a parent** (2.3). The README also has an error (2.4).
- Apart from the 44 duplicates in 1.2, no new class duplicates an existing one, even with normalized labels. I treated great toe/hallux/first toe, thumb/first finger, small/little/fifth finger, disk/disc, peroneal/fibular, tuberosity/tubercle and capitellum/capitulum as the same, and ignored "bone", "muscle" and "proper". In particular, the numbered toe, finger, metatarsal, rib and disk classes are genuinely new.

### 2.2 Wrong parents

| Row | Label | Table's parent | Problem | Suggested parent |
|---|---|---|---|---|
| RID51590 | cranial cavity (hand-picked) | RID32952 *body cavity subdivision* | RID32952 is under RID32950 *space of compartment of trunk*. Its children are thoracic, abdominal and pelvic spaces. This would put the cranial cavity in the trunk. FMA puts the cranial cavity (FMA:9644) under *Space of compartment of head* (FMA:84953), which RadLex lacks. | RID32949 *anatomical compartment space* (FMA:84926), the nearest RadLex ancestor. Or add a *space of compartment of head* class. |
| RID51121 | interphalangeal joint of great toe | RID34530 *interphalangeal joint* | Too general. RadLex has RID34532 *interphalangeal joint of toe*, the obvious closer parent. The finger side already has the matching pattern (RID34533 *interphalangeal joint of thumb* under the finger class). | RID34532 *interphalangeal joint of toe* |

### 2.3 Missing parent: permanent teeth

The 20 sided deciduous teeth (RID51985–RID52004) each get two parents: their tooth type and RID9131 *deciduous tooth*. The 32 sided permanent teeth (RID51953–RID51984) get only their tooth type, for example RID51953 *right maxillary central incisor tooth*, which sits under RID9127 *incisor tooth* alone. RadLex has RID9132 *permanent tooth*, a sibling of *deciduous tooth*. **Suggested fix:** add `RID:RID9132` as a second parent on the 32 permanent-tooth rows, so the two dentitions are modeled the same way.

A smaller point, for the group to decide: no unsided class sits between a sided tooth and its type, such as *maxillary central incisor tooth*. So *left* and *right maxillary central incisor tooth* share no parent closer than *incisor tooth*. That's fine for a first pass, and the Contained_In/Part_Of step (maxillary vs mandibular dental arcade) may cover it.

### 2.4 README error about the ribs

The README says the twelve numbered ribs go "under `RID28591` rib". The table puts them under `RID2471` *rib*, and the table is right: `RID28591` is *set of ribs*. The README should say `RID2471`.

The mix-up comes from the index itself. Its unsided "rib" entry uses `RID28591`, the set, which is why the combined IDs are `RID28591_RID6151` and so on. Choosing the parent by hand was the right call. That entry is worth reporting upstream, or fixing in the existing-entries step.

### 2.5 Hand-picked and "same kind" parents that are fine

- **Supratentorial and infratentorial brain** (RID51947, RID51948) under RID13853 *segment of brain* is correct. It matches FMA, where *Supratentorial region of brain* (FMA:322211) and *Infratentorial region of brain* (FMA:322212) are both direct children of *Segment of brain* (FMA:55676), which is the class RID13853 maps to. Adding the FMA codes from 1.3 would make this explicit.
- **Ribs** under RID2471 *rib*: correct (see 2.4).
- **Disks** C2/C3–C7/T1 under RID50392 *cervical intervertebral disk*, and L1/L2–L5/S1 under RID28830 *lumbar intervertebral disk*: correct. C7/T1 counts as a cervical disk, which matches FMA's naming by the upper vertebra.
- **Toes and fingers** (joints, phalanges, metatarsals): correct, except for 2.2. The thumb's phalanges go under the *finger* phalanx classes, which follows RadLex: RID2392 *thumb* is a subclass of *finger*, and existing classes such as RID39704 *proximal epiphysis of phalanx of thumb* sit under the matching finger class.
- **Deciduous teeth** with two parents: correct.
- **Sided rows whose unsided class is a group**, such as RID51481/RID51482 *left/right erector spinae muscle group* under RID7780: consistent. Their FMA codes (22732/22731) are also groups.

### 2.6 Already noted elsewhere

- The 44 duplicate rows in 1.2. None of them is a parent of another row.
- RID52005–RID52012, *left/right frontal/temporal/occipital/parietal brain region*, under RID6391–RID6394 (*… brain region*, under *body region*). The parent is correct for what these classes claim to be. The open question in 1.3 is whether they duplicate the existing sided lobes.

## 3. Labels and synonyms

The main concern here is errors of commission: a label or `oboInOwl:hasExactSynonym` that says something false or ambiguous. Missing names and acronyms come second (3.6).

### 3.1 Summary

- **The mechanical checks pass.** All 1,013 labels and 432 synonyms (on 251 rows) match the index's `description` and `synonyms` exactly, so the generator didn't change any text. There are no stray spaces, non-ASCII characters, trailing punctuation or brackets. No label is repeated in the table, and no synonym repeats a label, another row's synonym, or any existing RadLex label or synonym. Uppercase appears only in real acronyms and proper names: MTP, PIP, DIP, MCP, PICA, ADA, C2/C3, M1, Achilles.
- **Side is consistent.** Every synonym on a sided row names the same side as its label, except the tooth numbers, which encode side in the number (3.3).
- **Real errors:** six pairs of synonyms are broader than their class or ambiguous (3.2), and the tooth-number synonyms are ambiguous across numbering systems (3.3).
- **Inherited errors:** a few labels and synonyms copy misspellings from existing RadLex labels, and the comparison turned up three existing labels that are simply wrong (3.4).

### 3.2 Synonyms that aren't exact (remove, or change to a broader/related property)

| Row(s) | Label | Synonym | Problem |
|---|---|---|---|
| RID51783 / RID51784 | left / right medial orbitofrontal artery | left / right orbitofrontal artery | Broader. The lateral orbitofrontal artery is a separate branch of the MCA. These rows are duplicates (1.2), but **don't carry this synonym over to the existing classes** RID36415/RID36414 either. |
| RID51278 / RID51279 | left / right abductor digiti minimi muscle of foot | left / right abductor digiti minimi muscle | Ambiguous: the hand has an abductor digiti minimi too. The label includes "of foot" for exactly this reason. |
| RID51072 / RID51073 | left / right medial tubercle of talus | left / right medial tubercle | Ambiguous: medial tubercles exist on other bones too, such as the tibia's intercondylar eminence. It comes from the index's unsided synonym "medial tubercle", which is also RadLex's own label for RID2952. That label should become *medial tubercle of talus* in the existing-entries step. |
| RID51649 / RID51650 | left / right half of pharyngeal tonsil | left / right pharyngeal tonsil | The pharyngeal tonsil (adenoid) is a single midline structure, so a "left pharyngeal tonsil" doesn't exist. The label's "half of" is the accurate form. |
| RID51098 / RID51099 | left / right deep posterior tibiotalar ligament | left / right posterior tibiotalar ligament | Probably broader. The deltoid ligament has superficial and deep posterior tibiotalar bands in many descriptions. The unsided parent RID3016 is labeled *posterior tibiotalar ligament*, so either the parent is broader than this child, or the label's "deep" is redundant. Needs a decision, not just a synonym fix. |
| RID51566 / RID51567 | left / right mesorectal lymph node | left / right pararectal lymph node | Near-synonym. In rectal-cancer staging, "mesorectal" nodes lie inside the mesorectal fascia, while "pararectal" is the older anatomic term and is often used more loosely. FMA codes the unsided class as *Pararectal lymph node* (FMA:16621), and RadLex's RID466 is labeled that way. Acceptable, but it's the weakest of the remaining synonyms. |

### 3.3 Tooth numbers are ambiguous

The 52 sided teeth carry synonyms like `tooth 8` and `ADA 8` (permanent teeth), and `tooth E` and `ADA E` (deciduous). I checked every number and letter against the **Universal Numbering System**, and all are correct. But as plain exact synonyms they're ambiguous, because the **FDI/ISO 3950** system, used outside the US, gives the same numbers to different teeth. For example, `tooth 11` here is the left maxillary canine, while FDI 11 is the right maxillary central incisor. In all, 18 of the 32 numbers (11–18, 21–28, 31 and 32) are also valid FDI numbers for a different tooth. The deciduous letters don't collide. "ADA" doesn't fix this, since the ADA recognizes both systems.

**Suggested fix:** name the system in the synonym (e.g. `Universal tooth 8`), or move the numbers to a notation property that names the system. I'd also consider adding the FDI numbers the same way (e.g. `FDI tooth 11` on the right maxillary central incisor). RadLex has no tooth-numbering synonyms today, so this would set the pattern.

### 3.4 Errors inherited from existing RadLex labels

When a sided row's label differs from its parent's label, it's usually because the parent's RadLex label is wrong. The new row then gets it right but copies the wrong form as a synonym. These are fixes for the existing-entries step, but the synonyms on the new rows should be decided at the same time:

| Existing class | RadLex label | Correct form | Effect on new rows |
|---|---|---|---|
| RID7819 | *extensor coccygis muscle* | *coccygeus muscle*. The class's own synonyms (*coccygeus*, *ischiococcygeus*), its parent (*pelvic floor muscle*), the index, and FMA:19088 all say coccygeus. The extensor coccygis is a different, vestigial back muscle. | RID51548/RID51549 *right/left coccygeus muscle* are correctly labeled, but sit under a parent with the wrong label. |
| RID9862 | *risoris muscle* | *risorius muscle* | RID51885/RID51886 use the correct spelling. |
| RID9853 | *depressor labii inferior muscle* | *depressor labii inferioris muscle* | RID51881/RID51882 have the correct label, but also the incorrect form `left/right depressor labii inferior muscle` as an exact synonym. Drop it, unless RadLex deliberately keeps common misspellings. |
| RID2703 | *tensor fascia lata muscle* | *tensor fasciae latae muscle* | RID51252/RID51253: same pattern (`tensor fascia lata` synonym). This form is common enough in reports that keeping it as a synonym is defensible. |
| RID34263 | *Intramammary lymph node* | *intramammary lymph node* (lowercase) | None. |

### 3.5 Labels that differ from their parent's wording (consistency, not errors)

76 sided rows use wording that differs from their unsided parent's RadLex label. Apart from the cases in 3.2 and 3.4, the labels are all acceptable terms, but RadLex will read inconsistently if parent and child use different preferred terms. The main groups:

- **Child uses the newer or TA term, parent the older:** *great/small saphenous vein* under *greater/lesser saphenous vein*; *dorsalis pedis artery* under *dorsal pedal artery*; *palmar radioulnar ligament* under *volar radioulnar ligament*; *tympanic cavity* under *middle ear cavity*; *superior semicircular canal* under *anterior semicircular canal*; *talar sulcus* under *sulcus tali*; *renal calyx* under *calyx of renal collecting system*; *mesorectal lymph node* under *pararectal lymph node*.
- **Child drops a word the parent has:** *left superior/middle/inferior meatus* under *… nasal meatus*, and *left superior/middle/inferior turbinate* under *… nasal turbinate* (RID51755–RID51768). The synonyms carry the "nasal" form. *Left/right flexor digitorum brevis muscle* is under *flexor digitorum brevis muscle of foot*. *Left/right retropharyngeal space* is under *retropharyngeal space of head*. I'd make "nasal" part of the label: a bare "superior meatus" is ambiguous in a terminology that also has auditory meatuses.
- **Child adds a word or spells out an acronym:** the PICA segments spell out *posterior inferior cerebellar artery*, while their parents say *PICA*. The child is better here, so the parents' labels could be expanded. Also *accessory breast tissue* under *accessory breast*.

**Suggested rule:** a sided label is "left/right" plus the parent's label, with any other wording as a synonym. Where the child's wording is better, change the parent's label in the existing-entries step instead. The full list of 76 is easy to regenerate (1.6 describes the method).

### 3.6 Missing synonyms and acronyms (secondary)

**How RadLex uses acronyms today.** `RID:Acronym` appears on just 145 classes (e.g. *internal carotid artery* "ICA", *anterior cruciate ligament* "ACL", *temporomandibular joint* "TMJ", the cranial nerves "CN I"–"CN XII"), and never on a left or right class. So the empty `Acronyms` column fits RadLex's practice for the 876 sided rows. Acronyms belong on the unsided classes, most of which already exist.

**Acronyms worth adding to the unsided parents** (existing-entries step). Each is in routine use in radiology reports:

| Parent | Acronym |
|---|---|
| RID584 common carotid artery | CCA |
| RID684 external carotid artery | ECA |
| RID944 / RID957 common / external iliac artery | CIA / EIA |
| RID958 common femoral artery | CFA |
| RID961 superficial femoral artery | SFA |
| RID959 deep femoral artery | DFA (also PFA, profunda femoris artery) |
| RID971 / RID967 anterior / posterior tibial artery | ATA / PTA |
| RID1024 internal jugular vein | IJV |
| RID1197 / RID1202 greater / lesser saphenous vein | GSV / SSV |
| RID3022 / RID3024 anterior / posterior talofibular ligament | ATFL / PTFL |
| RID3023 calcaneofibular ligament | CFL |
| RID38808 / RID38809 anterior / posterior tibiofibular ligament | AITFL / PITFL |
| RID2203 distal radioulnar joint | DRUJ |
| RID2259 scapholunate ligament | SLL (also SLIL) |
| RID10094 / RID9392 external / internal auditory canal | EAC / IAC |
| RID7500 sternocleidomastoid muscle | SCM |
| RID2703 tensor fasciae latae muscle | TFL |
| RID9590 / RID9591 superior / inferior orbital fissure | SOF / IOF |
| RID2332 / RID3129 metacarpophalangeal / metatarsophalangeal joint | MCP / MTP |
| RID2408 / RID3139 proximal interphalangeal joint of finger / toe | PIP |
| RID2418 / RID3148 distal interphalangeal joint of finger / toe | DIP |
| RID34530 interphalangeal joint | IP |

PIP, DIP and MTP are tagged per class, not globally unique; "PIP" on both the finger and toe classes matches how they're used. PICA, AICA and the parent cerebral arteries (ACA, MCA, PCA) aren't parents of rows in this table, so they're outside its scope.

**The new unsided rows.** The joint rows already have acronym-style names as exact synonyms (`first MTP`, `1st MTP`, `PIP joint of second toe`, `2nd finger DIP joint`). Should RadLex keep those as synonyms or move them to `RID:Acronym`, the way it stores "CN I"? That's a style decision for the group. Either way, the forms are correct.

**Synonyms clearly missing:**

- **Disks.** The 11 disk rows have no synonyms, and their labels use the slash form (`C5/C6 cervical intervertebral disk`). Reports usually write `C5-C6` or `C5-6`, and RadLex already gives *disc* spellings to its disk classes (RID7890 *intervertebral disc*, RID28830 *lumbar intervertebral disc*). Add, for example, `C5-C6 intervertebral disk`, `C5-6 disc` and `C5/C6 cervical intervertebral disc` to each row.
- **Fingers.** The small-finger rows have *fifth finger* but not *little finger*. The thumb rows have *first finger*, which is fine. The great-toe rows have *first toe* and *1st toe*, but not *hallux*, which is the usual term in foot imaging (e.g. *proximal phalanx of hallux*).
- **Ribs.** These are fine as they are (*1st rib*, etc.).

## 4. Proposed definitions

The index has no definitions for these entries, but the contributing guide asks for one on each new class. `proposed-definitions.tsv`, next to this file, proposes one for every row. It has four columns: `RadLex ID`, `ALI ID`, `Label`, `Proposed definition`. The definitions were drafted with AI assistance and haven't been checked by a domain expert yet. They follow the genus–differentia form ("A *X* that …") and end with a period.

### 4.1 How they were written

| Kind | Rows | Form |
|---|---|---|
| Sided, parent is an existing class: one per side | 654 | "The *structure* on the left/right side of the body", with "the" inside "of" phrases, e.g. "The head of the femur on the left side of the body." |
| Sided, parent is an existing class: several per side | 60 | "A/An *structure* located on the left/right side of the body", e.g. "An inguinal lymph node located on the left side of the body." Used for structures with several per side (lymph nodes, lenticulostriate and thalamoperforating arteries, paired venae comitantes, renal calyces, foot lumbricals and interossei, metacarpal bone, glenohumeral ligament, adrenal artery, superficial and inferior cerebral veins), or whose label doesn't say which one is meant (unqualified extensor/flexor retinaculum, fold of incus). |
| Sided, mass noun | 2 | "Accessory breast tissue located on the left side of the body." The *structure* is the label without its side word, with "nasal" restored on the meatuses and turbinates, and "of foot" on flexor digitorum brevis (3.5). | The structure is the label without its side word, with "nasal" restored on the meatuses and turbinates, and "of foot" on flexor digitorum brevis (3.5). |
| Sided, parent is a new class | 142 | The parent's hand-written definition, plus ", on the left/right side of the body." For ribs, the side goes right after "rib". |
| Sided teeth | 52 | "The permanent / deciduous (primary) *tooth type* of the right/left upper (maxillary) / lower (mandibular) quadrant of the dentition." |
| Unsided, new | 85 | Hand-written: the numbered toe and finger joints and bones (by articulation), ribs (true/false/floating), disks (by the vertebrae on either side), cranial cavity, supratentorial and infratentorial brain. |
| Midline structures | 8 | "The part of the *X* to the left/right of the midsagittal plane." Used for the half of the pharyngeal tonsil, retropharyngeal space, perivertebral space and lingual tonsil, which are single midline structures. |
| Brain regions | 8 | "The *frontal brain region* in the left/right cerebral hemisphere." |
| Uterine adnexa | 2 | Written out (uterine tube, ovary and supporting ligaments), because "adnexa" is plural. |

### 4.2 Points for a reviewer

- **The 44 duplicate rows (1.2) have definitions too,** so the file covers every row. Ignore them if those rows are dropped.
- **"The" vs "a".** "The" reads naturally to clinicians (there is one left leg), and it's accurate wherever each side has exactly one. The 30 structures kept on "a/an" are a hand-picked list. Please check it, especially the borderline ones: the superior vesical and lateral posterior choroidal arteries (often more than one), and the retinacula and fold of incus (ambiguous labels).
- **The template definitions** add almost nothing beyond the label. They're accurate, but they're only as good as the parent class's own definition, and most parents have none. A domain expert could reasonably prefer to leave sided classes undefined, or to define them only when the parent is defined. That's a policy choice for the group.
- **Check these hand-written definitions** most carefully:
  - *Infratentorial brain* includes the midbrain, following the usual radiology convention, even though the midbrain passes through the tentorial notch.
  - Ribs: the eighth to tenth ribs are "false", and the eleventh and twelfth "floating". The tenth rib is sometimes floating as a normal variant; the definition doesn't mention that.
  - Phalanges of the fifth toe: the middle and distal phalanges are often fused. The definitions describe the typical anatomy.
- **The midline-structure definitions** depend on the "part to one side of the midline" reading. That's the only coherent meaning of "left retropharyngeal space" and the others, but the group should accept it explicitly.
- **Provenance.** The contributing guide wants the source in `RID:Source`. These rows already carry `Anatomic Locations Index 1.0.1` there, which doesn't describe where the definitions came from. Options: a second `RID:Source` value such as "RadLex editors", or a definition-level source annotation (e.g. `oboInOwl:hasDbXref` on the `obo:IAO_0000115` axiom). Either way, the definitions should be marked as drafted with AI assistance until reviewed.
- **Applying them.** The `Definition` column in `new-classes.tsv` already maps to `obo:IAO_0000115` and is empty. The generator could read this file by `ALI ID` and fill that column.

## 5. RID range and code prefixes

- **The RID range is fine as stated.** The 1,013 rows use `RID51000`–`RID52012`, consecutive in file order with no gaps, and every `RadLexID` value matches its row's IRI. None of these RIDs is used in `RadLex.owl` today. The README says the highest RID in use is `RID50784`, but this branch's `RadLex.owl` now goes up to `RID50859`. That's still well below `RID51000`, so there's no conflict, but the README's figure is out of date.
- **Provenance:** accepted as it is (Jeff, 2026-11-23).
- **Prefixes in Bioregistry** (checked 2026-11-23 via `bioregistry.io/api/registry/<prefix>`):
  - `snomedct`: **registered** as "Systematized Nomenclature of Medicine - Clinical Terms". Bioregistry also accepts `SNOMEDCT`, `SCTID` and `SNOMED` as synonyms, so the table's `SNOMEDCT:` prefix resolves.
  - `fma` and `umls`: registered. `radlex` is registered too, with the pattern `^RID\d+$`.
  - `ta2`: **not registered**, and neither is `ta98`. Bioregistry has the sibling terminologies Terminologia Embryologica (`te`) and Terminologia Histologica (`th`), but not Terminologia Anatomica, in either edition.
  - Anatomic Locations (`ANAT_LOC`): **not registered.**
  - Both could be added through a new-prefix request to Bioregistry. Each needs a name, homepage, example ID, and a pattern (`^\d+$` for TA2, `^RID\d+(_RID\d+)*$` for Anatomic Locations). A URI format would also help, if the TA2 site and anatomiclocations.org have stable per-term URLs.
