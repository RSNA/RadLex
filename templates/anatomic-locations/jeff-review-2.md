# Review of `new-classes.tsv`, round 2

New findings from 2026-11-24/25, after the first review in [`jeff-review.md`](jeff-review.md). It has two parts. Section 0 checks each item from the first review against the revised table and PR #55, and says which are still open. Sections 1–3 hold new findings from a second pass with UMLS: a check of the synonyms, and a few cross-reference findings that check turned up.

**Table checked.** `new-classes.tsv` at commit a1f9ea6 on `add-anatomic-locations-classes`. It's identical to the table in PR #55 (`add-anatomic-locations-new-classes`). It has 967 classes, RID51000–RID51966, and **all RIDs below use that numbering**. They don't match the RIDs in `jeff-review.md`, which used the draft's numbering. Where it helps, rows are also identified by their Anatomic Locations ID.

**Sources.** UMLS Metathesaurus 2026AB through the UTS REST API, which includes SNOMED CT US Edition 2026-09-01 and FMA 4.15. FMA 5.1.0 via EBI OLS, to confirm FMA codes. RadLex itself isn't in UMLS.

## Summary

- **The synonyms flagged in the first review are still in the table, and PR #55 adds them to `RadLex.owl` as exact synonyms** (0.1). The PR's README lists them as "still open". But once the PR merges, they're in the release. I'd remove the clearly wrong ones before it merges.
- **No errors of commission in the synonyms.** No synonym in the table belongs to a different UMLS concept, except three that are UMLS's own errors (3).
- **The 75 `UMLS:` codes added since the first review are correct.** Each CUI exists and is the same CUI as the row's FMA or SNOMED CT code, and the sides agree (1.1).
- **FMA has classes for the A2 and M3 segments, but they're broader.** My first review missed them. They'd be broad matches only (1.2).
- **P3: more evidence that the P3 rows duplicate the lateral occipital artery classes.** This is for the decision Tarik held back (1.3).
- **Tooth numbers: UMLS confirms all 52**, and SNOMED CT can supply the FDI numbers (2).
- **About 35 standard synonyms worth adding** (3).

## 0. Status of the first review's items

Checked on 2026-11-25 against `new-classes.tsv` at a1f9ea6. That's the same table as PR #55, where it has been merged into `RadLex.owl`. Section numbers in this part refer to `jeff-review.md`.

### 0.1 Still open, and in PR #55's `RadLex.owl`

These are synonyms the first review flagged as wrong or ambiguous. Tarik changed no labels or synonyms in the revision, so all of them are still there. PR #55's README lists 3.2 and 3.3 as "still open", but the PR still adds them all to `RadLex.owl` as `oboInOwl:hasExactSynonym`.

| Review | Rows (new RIDs) | Exact synonym in PR #55 | Problem | Suggestion |
|---|---|---|---|---|
| 3.2 | RID51266 / RID51267 *left/right abductor digiti minimi muscle of foot* | *left/right abductor digiti minimi muscle* | Ambiguous: the hand has one too | Remove before merge |
| 3.2 | RID51070 / RID51071 *left/right medial tubercle of talus* | *left/right medial tubercle* | Ambiguous: other bones have medial tubercles | Remove before merge |
| 3.2 | RID51615 / RID51616 *left/right half of pharyngeal tonsil* | *left/right pharyngeal tonsil* | Wrong: the pharyngeal tonsil is a single midline structure | Remove before merge |
| 3.2 | RID51096 / RID51097 *left/right deep posterior tibiotalar ligament* | *left/right posterior tibiotalar ligament* | Probably broader (superficial and deep bands) | Remove, or settle "deep" first |
| 3.2 | RID51532 / RID51533 *left/right mesorectal lymph node* | *left/right pararectal lymph node* | Near-synonym | Acceptable; could be a related synonym |
| 3.3 | All 52 sided teeth | `tooth N` / `ADA N` (104 synonyms) | 18 of the 32 permanent-tooth numbers name a different tooth in the FDI system (e.g. `tooth 11`) | Remove before merge, or qualify them (`Universal tooth 11`) |
| 3.4 | RID51835 / RID51836 *left/right depressor labii inferioris muscle* | *left/right depressor labii inferior muscle* | Misspelling, copied from the existing RID9853 label | Remove before merge. **Not on the PR's "still open" list.** |
| 3.4 | RID51248 / RID51249 *left/right tensor fasciae latae muscle* | *left/right tensor fascia lata muscle* | Common non-Latin form | Defensible as is |

Exact synonyms in a release are hard to take back once tools pick them up. The first four rows and the tooth numbers are the ones I'd fix in PR #55 itself rather than later. The 3.2 row the first review flagged on *medial orbitofrontal artery* is gone: those rows were removed as duplicates.

### 0.2 Still open, not in the PR's "still open" list

- **TA2 codes (1.4).** The cranial cavity (RID51556) still has two TA2 codes, `TA2:100` and `TA2:413`; check which is right. The eleventh and twelfth ribs (RID51490, RID51493) still have no TA2 code, though TA2 lists them.
- **Missing synonyms (3.6, secondary).** The 11 disks still have no synonyms (`C5-C6`, `C5-6 disc`, …). None of the 18 small-finger rows has *little finger*, and none of the 12 great-toe rows has *hallux*. Section 3 adds more candidates from UMLS.
- **Label wording versus parent (3.5).** No labels changed, so the 76 sided labels whose wording differs from their parent's still do. This is about consistency, not errors.
- **Definitions (4).** The PR says "None are given". Its README no longer mentions `proposed-definitions.tsv`, which is only on this branch.

### 0.3 Open, and listed in the PR

- **FMA codes that need a decision (1.3):** wrist joint (RID51320/RID51321, FMA 35299/35298), common femoral artery (RID51210/RID51211, FMA 70250/70249), deep posterior tibiotalar ligament (RID51096/RID51097, FMA 44071/44070). The last ties in with the synonym question in 0.1.
- **P3 segment:** held back; see 1.3 below for new evidence.
- **New code prefixes (5).**

### 0.4 Addressed

- The 44 duplicates (1.2) were removed and listed in `already-in-radlex.tsv`.
- The parent fixes (2.2, 2.3): cranial cavity is under RID32949. The interphalangeal joint of the great toe is under RID34532. All 32 permanent teeth are also under RID9132 *permanent tooth*.
- 22 FMA codes from 1.3 were added: the ankle ligament parts, the posterior compartments, ten disks, and the supratentorial and infratentorial brain.
- The weaker FMA matches (1.3) weren't added, as I recommended. The sided brain regions stay as new classes ("a brain region is not a lobe").
- Head of fibula: Tarik judged it distinct from the proximal epiphysis and kept those rows. UMLS puts the two under one concept, but FMA keeps them apart, so I accept this. The placement of RID39763/RID39762 under *head of fibula* is left for the existing-classes step, as his README says.
- The README's rib error (2.4) is fixed.
- 75 `UMLS:` codes were added. All are correct (1.1).

## 1. Cross-references

### 1.1 The new `UMLS:` codes

The revised table adds `UMLS:` codes to 75 classes. All 75 are correct:

- Every CUI exists in UMLS 2026AB.
- On every row, the CUI is the same as the CUI of the row's FMA or SNOMED CT code.
- The CUI's name has the same side as the label.

### 1.2 FMA codes for the A2 and M3 segments: broader, so not exact matches

In `jeff-review.md` (1.3) I said FMA 5.1 had nothing for the A2, M3, M4 and P3 segments. That was wrong for A2, M3 and P3. FMA names cerebral artery segments by their Terminologia Anatomica *part* (FMA 4.15 also lists the segment name as a synonym), so my label search missed them. All of these codes are active in FMA 5.1:

| Rows | Anatomic Locations ID | FMA (left / right) | Fit |
|---|---|---|---|
| RID51747 / RID51748 *left/right A2 segment of anterior cerebral artery* | RID651_RID5824 / RID651_RID5825 | 50078 / 50077 *postcommunicating part of anterior cerebral artery* | Broader. In TA the postcommunicating part runs from the anterior communicating artery onward, i.e. A2 and beyond. In radiology, A2 ends at the genu of the corpus callosum. |
| RID51753 / RID51754 *left/right M3 segment of middle cerebral artery* | RID680_RID5824 / RID680_RID5825 | 79635 / 79634 *cortical part of middle cerebral artery* | Broader. The cortical part covers M3 and M4, and the table has M4 rows too. |

**Suggestion:** don't add either pair as an exact `RID:ExternalRefID`. If RadLex later gets a property for broad matches, these would fit there. The table's A1, P1 and P2 rows already carry the *precommunicating* and *postcommunicating part* codes, which are exact for those segments. FMA has nothing for M4.

### 1.3 P3 segment and lateral occipital artery (Tarik's held-back pair)

`already-in-radlex.tsv` holds back RID818_RID5824 / RID818_RID5825 *left/right P3 segment of posterior cerebral artery* and asks whether P3 and the lateral occipital artery are the same structure. Evidence that they are:

- FMA 4.15 lists "P3 segment of left posterior cerebral artery" as a synonym on FMA:50644 *left lateral occipital artery*, and likewise on the right (50643). UMLS puts the two names under one concept (C0923814 left, C0923813 right).
- Terminologia Anatomica gives the lateral occipital artery as P3.
- RadLex already gives the unsided P3 class (RID818) the synonym *arteria occipitalis lateralis*, as Tarik notes.
- The sided lateral occipital artery classes, RID44763 / RID44762, already carry FMA:50644 / 50643.

So I'd treat them as the same structure: keep the two rows out, and add "left/right P3 segment of posterior cerebral artery" as synonyms of RID44763 / RID44762. The existing classes are inconsistent, though: RID44763 / RID44762 sit *under* RID818 *P3 segment*, as if the lateral occipital artery were a kind or part of P3. That's for the existing-entries step. Either make the sided lateral occipital arteries the sided P3 classes, or merge the names.

## 2. Tooth numbers

All 52 tooth synonyms (`tooth 8`, `ADA 8`, `tooth E`, `ADA E`, …) match the "Universal designation" synonym on the row's SNOMED CT concept, including the lettered deciduous teeth A–T. This confirms the check in `jeff-review.md` (3.3).

For the FDI numbers suggested there, SNOMED CT gives each tooth an "ISO designation" synonym (e.g. ISO 51 for the right deciduous maxillary central incisor). So FDI forms such as `FDI tooth 11` can be generated from the codes the table already has. They don't need to be compiled by hand.

## 3. Synonyms and acronyms against UMLS

**Method.** For each row, I took the UMLS concepts (CUIs) of its FMA and SNOMED CT codes. For 6 rows with neither code, I found the CUI by searching the label: the glenohumeral ligaments and the A2 and M3 segments. 92 rows have no CUI either way; they're mostly the newer index entries (PICA segments, neck spaces, posterior leg compartments, brain regions). I then looked up each synonym with UMLS's normalized-string search.

**Errors of commission: none found.** The table has 426 synonyms and no acronyms:

| Result | Synonyms |
|---|---|
| UMLS puts it on the row's own concept | 161 |
| Not in UMLS at all | 240 |
| Row has no CUI, so not checkable | 22 |
| UMLS puts it only on a different concept | 3 |

The three in the last group are UMLS artifacts, not table errors:

- *left/right dorsal pedal artery* (RID51238 / RID51239) only matches a LOINC "part" concept.
- *right maxillary cuspid tooth* (RID51909) matches an old SNOMED 2 term, "Maxillary right cuspid tooth", which UMLS has misfiled under the *mandibular* right canine. The table's synonym is correct.

The 240 not in UMLS are expected:

- 52 are the tooth numbers and letters (2).
- Almost all the rest are ordinal and abbreviated forms UMLS doesn't carry: `2nd MTP`, `PIP joint of third toe`, `4th finger proximal phalanx`, `1st rib`.
- The rest were already flagged in `jeff-review.md`:
  - the inexact synonyms in its 3.2 (*medial tubercle*, *pharyngeal tonsil*, *orbitofrontal artery*, *abductor digiti minimi*);
  - `depressor labii inferior` and `tensor fascia lata` (its 3.4).

**Acronyms.** UMLS has no standalone acronyms for these concepts. Its only abbreviations are SNOMED/Read forms such as `MTPJ2 - Second metatarsophalangeal joint`, which support the MTP/PIP/DIP forms the table already has. The acronym list in `jeff-review.md` (3.6) stands.

**Missing synonyms (secondary).** UMLS offers about 1,470 English terms for these concepts that aren't on the rows. Most are FMA/UWDA phrasing variants ("Second proximal phalanx of left foot"), Latin, or word-order changes. (UWDA is the University of Washington Digital Anatomist, an older FMA-derived source.) Here are the ones I'd add, each from FMA or SNOMED CT. Each applies to both sides (e.g. *left innominate vein* on the left brachiocephalic vein):

| Rows | Add |
|---|---|
| brachiocephalic vein | innominate vein |
| ilium | iliac bone |
| head of femur / head of radius | femoral head / radial head |
| capitellum of humerus | capitulum of humerus |
| ankle joint | talocrural joint |
| Achilles tendon | calcaneal tendon |
| deep femoral artery | profunda femoris artery |
| small saphenous vein | short saphenous vein |
| peroneal vein / common peroneal nerve | fibular vein / common fibular nerve (current TA terms) |
| quadratus plantae muscle | flexor accessorius muscle |
| greater / lesser tuberosity of humerus | greater / lesser tubercle of humerus |
| distal radioulnar joint | inferior radioulnar joint |
| triquetrum | triquetral bone |
| vas deferens | ductus deferens |
| anterior / middle / posterior scalene muscle | scalenus anterior / medius / posterior |
| superior / middle / inferior constrictor muscle | superior / middle / inferior pharyngeal constrictor muscle (the labels don't say "pharyngeal") |
| palatine tonsil | faucial tonsil |
| globe | eyeball |
| external / internal auditory canal | external / internal acoustic meatus |
| eustachian tube | pharyngotympanic tube |
| lateral process of malleus | short process of malleus |
| long / short process of incus | long / short limb of incus |
| footplate of stapes | base of stapes |
| superior / middle / inferior turbinate | superior / middle / inferior nasal concha |
| transverse sinus | lateral sinus |
| A1 / P1 segment | precommunicating part of anterior / posterior cerebral artery |
| P2 segment | postcommunicating part of posterior cerebral artery |
| M1 / M2 segment | sphenoidal (horizontal) part / insular part of middle cerebral artery |
| common tendinous ring of extraocular muscles | common annular tendon |
| transverse / vertical muscle of tongue | transverse / vertical lingual muscle |
| retromolar trigone | retromolar area |
| condyle of mandible | condylar process of mandible |
| leg | lower leg |

I left out A2 and M3, because their UMLS terms are broader (1.2). I also left out the disks: UMLS's FMA forms (`C2 disk`, "intervertebral disk of second cervical vertebra") name a disk by the vertebra above it, which invites confusion. The SNOMED forms (`C4/5 disc`, `L5-S1 disc`) are already covered by `jeff-review.md` (3.6).

## 4. How these checks were run

The scripts are in the session scratchpad, not the repo. All UTS calls were throttled to 5 requests per second and cached; NLM's limit is 20 per second per IP address.

1. Find each row's CUIs from its FMA and SNOMED CT codes (`/search/current?inputType=sourceUi&searchType=exact&sabs=…`). For rows with neither code, use a `normalizedString` search on the label.
2. Look up each synonym with a `normalizedString` search, and compare the CUIs it hits with the row's.
3. Collect the English atoms of each row's CUIs (`/content/current/CUI/<cui>/atoms`). Drop those already on the row, and pick out the standard terms by hand.
4. Compare the tooth synonyms with the SNOMED CT "Universal designation" atoms.
5. Check each `UMLS:` code with `/content/current/CUI/<cui>`, and compare it with the CUIs of the row's other codes.
6. Confirm the FMA codes in 1.2 and 1.3 by IRI in FMA 5.1.0 on OLS.
