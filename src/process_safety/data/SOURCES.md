# SOURCES.md

Sources used to ground the answer keys, distractor rationales, and reasoning rubrics in
`data/process_safety.jsonl`. Scope is **Great Britain** (England, Scotland, Wales) unless an
item deliberately tests the GB-vs-NI / GB-CLP-vs-EU-CLP distinction.

**Verification basis:** confirmed current as of **June 2026** against HSE (hse.gov.uk) and
legislation.gov.uk primary sources, supplemented by a structured research pass. Where a fact
was first seen on a commercial regulatory-news tracker, it was cross-checked against an HSE or
legislation.gov.uk primary source before use; **only primary sources are cited in answer keys.**

> **Do not invent citations.** Every `source` field in the JSONL traces to an entry below. The
> `source` strings are short citations (document + clause/section) by design; the full URLs and
> caveats live here.

---

## 1. DSEAR — Dangerous Substances and Explosive Atmospheres Regulations 2002

| Item | Reference | URL |
|---|---|---|
| Regulation | Dangerous Substances and Explosive Atmospheres Regulations 2002, SI 2002/2776 | https://www.legislation.gov.uk/uksi/2002/2776 |
| ACOP & guidance | L138 (2nd edition, 2013), *Dangerous substances and explosive atmospheres* | https://www.hse.gov.uk/pubns/books/l138.htm |
| 2015 scope extension | CLP (Amendments to Secondary Legislation) Regulations 2015 — extended DSEAR scope from 1 June 2015 | (HSE L138 page, above, carries the standing notice) |
| Short guide | INDG370, *Fire and explosion: how safe is your workplace?* | https://www.hse.gov.uk (INDG370) |
| Petrol road tankers | L133, *Unloading petrol from road tankers* (separate ACOP) | https://www.hse.gov.uk/pubns/books/l133.htm |

**Supports:** DSEAR-vs-COSHH scope mapping (mcq-006); hazardous-area zoning, gas/vapour Zones
0/1/2 vs dust 20/21/22 (mcq-007); the **post-2015 scope** covering gases under pressure and
substances corrosive to metals (mcq-008); the reg 6 elimination/reduction hierarchy and
prevention-before-mitigation (mcq-009, rsn-003); DSEAR+COSHH dual application (rsn-004).

**Currency caveat (IMPORTANT):** the 2002 SI's core text was not rewritten, but the scope was
**extended from 1 June 2015** so that "dangerous substance" is keyed to CLP physical hazard
classes, bringing **gases under pressure** and **substances corrosive to metals** within DSEAR.
Frame all DSEAR-scope items on the post-2015 definition. ACOP L138 remains the **2nd edition
(2013)** — treat any "2020 DSEAR ACOP" as wrong.

---

## 2. COSHH — Control of Substances Hazardous to Health Regulations 2002 (as amended)

| Item | Reference | URL |
|---|---|---|
| Regulation | COSHH Regulations 2002, SI 2002/2677 (as amended) | https://www.legislation.gov.uk/uksi/2002/2677 |
| ACOP & guidance | L5 (6th edition, 2013), *Control of substances hazardous to health* | https://www.hse.gov.uk/pubns/books/l5.htm |
| Eight principles | HSE, *Principles of good control practice* (COSHH Schedule 2A) | https://www.hse.gov.uk/coshh/detail/goodpractice.htm |

**Supports:** COSHH scope exclusion of lead (mcq-010); the **eight principles are not ranked**
(mcq-011); health-surveillance triggers under reg 11 (mcq-013); PPE-as-last-resort / adequate
control (rsn-005); assess-before-work and adequate control criteria (rsn-006).

**Currency caveat:** L5 is still the **6th edition (2013)**; no 2024–2026 COSHH amendments found.
Note one HSE "related content" link mislabels it 5th edition — the L5 page itself confirms 6th.
**Lead, asbestos and (largely) radioactive substances are outside COSHH** and have their own
regimes (relevant to mcq-010).

---

## 3. EH40 — Workplace Exposure Limits

| Item | Reference | URL |
|---|---|---|
| WEL list | EH40/2005 *Workplace exposure limits* (4th edition, 2020) | https://www.hse.gov.uk/pubns/books/eh40.htm |
| Concept guidance | HSE, *Workplace exposure limits* | https://www.hse.gov.uk/coshh/basics/exposurelimits.htm |

**Supports:** STEL (15-minute reference period) vs long-term 8-hour TWA (mcq-012), used together
with COSHH for the WEL concept.

**Currency caveat:** EH40/2005 **4th edition (2020)** remains current; no new GB WELs or new
edition 2024–2026. EU Directive (EU) 2024/869 (diisocyanates; tighter lead) applies to **EU/NI,
not GB**. The dataset deliberately tests the **STEL/TWA concept**, not recall of specific numeric
limits (consistent with the defensive scope).

---

## 4. GB CLP — Classification, Labelling and Packaging

| Item | Reference | URL |
|---|---|---|
| Regulation | Assimilated Regulation (EC) No 1272/2008 as amended for GB ("GB CLP"); HSE is GB CLP Agency | https://www.hse.gov.uk/chemical-classification/legal/clp-regulation.htm |
| GB MCL list | GB Mandatory Classification and Labelling list (cited by **published / last-updated dates**, not edition numbers) | https://www.hse.gov.uk/chemical-classification/classification/mcl-list.htm |
| 2026 change | SI 2026/484, *The Chemicals (Health and Safety) (Amendment, Consequential and Transitional Provision) Regulations 2026* | https://www.legislation.gov.uk/uksi/2026/484 |
| 2026 change (HSE) | HSE, *Changes to the GB CLP Regulation* (notification removal from 21 May 2026) | https://www.hse.gov.uk/chemical-classification/legal/changes-gb-clp-regulation.htm |
| Pictograms / statements | HSE chemical-classification pages; GHS hazard pictograms, signal words, H- vs P-statements | https://www.hse.gov.uk/chemical-classification/ |

**Supports:** H- vs P-statement distinction (mcq-001); GB-vs-EU divergence on new hazard classes
(mcq-002, rsn-002); pictogram-to-hazard mapping (mcq-003); signal-word selection (mcq-004,
rsn-001); **SI 2026/484 removal of the GB C&L notification duty** (mcq-005).

**Currency caveats (MOST CHANGE-PRONE AREA):**
- **Nomenclature:** HSE publishes the GB MCL list by **publication / last-updated dates**, not
  edition numbers (the portal shows, e.g., "Published: 17 February 2025" and "Last updated:
  22 September 2025"). **Cite the dates, never a "6th"/"7th edition."** Confirm the live dates on
  the HSE portal at point of release.
- **SI 2026/484 (laid 24 Feb 2026; approved 21 Apr 2026):** from **21 May 2026** the duty to
  notify HSE of a substance's classification and labelling is **removed** for GB-based
  manufacturers/importers and NI suppliers directly supplying GB; the GB CLP **technical notes were
  moved into the GB MCL list**; and GB harmonised-classification updates are now more flexible
  (may occur without a fresh statutory instrument). The EU/NI C&L notification/inventory obligation
  is **separate and persists**.
- **GB-vs-EU divergence:** GB has **not** adopted the EU's new hazard classes (endocrine
  disruptors ED, PBT/vPvB, PMT/vPvM, via EU 2023/707) or the EU 2024/2865 labelling revision; NI
  follows EU CLP via the Windsor Framework. mcq-002 is **date-sensitive** — re-verify before
  release.

---

## 5. General duties & risk-assessment framework

| Item | Reference | URL |
|---|---|---|
| General duties | Health and Safety at Work etc. Act 1974, ss. 2, 3, 6 (and s.40 reverse burden) | https://www.legislation.gov.uk/ukpga/1974/37 |
| Risk assessment duty | Management of Health and Safety at Work Regulations 1999, reg 3 | https://www.legislation.gov.uk/uksi/1999/3242 |
| ALARP | *Edwards v National Coal Board* [1949] 1 All ER 743 ("gross disproportion" test); HSE R2P2 | https://www.hse.gov.uk/managing/theory/alarpglance.htm |

**Supports:** s.2 employer duty (mcq-018); s.3 duty to non-employees (mcq-019); the "reasonably
practicable" / ALARP test (mcq-020, rsn-010); MHSWR reg 3 suitable-and-sufficient assessment and
recording at 5+ employees (mcq-021, rsn-009).

**Currency caveat:** HSWA 1974 and MHSWR 1999 are long-standing and stable. The ALARP "gross
disproportion" standard is settled law (*Edwards v NCB*).

---

## 6. Hierarchy of control

| Item | Reference | URL |
|---|---|---|
| General hierarchy | HSE / NIOSH hierarchy of control (elimination → substitution → engineering → administrative → PPE) | https://www.hse.gov.uk/ (risk management); https://www.cdc.gov/niosh/hierarchy-of-controls/about/index.html |
| COSHH linkage | COSHH reg 7 control hierarchy + Schedule 2A good control practice | https://www.hse.gov.uk/coshh/detail/goodpractice.htm |

**Supports:** elimination as top tier (mcq-014); administrative-vs-engineering classification
(mcq-015); PPE-as-last-resort and respirators-are-PPE (mcq-016); substitution must not introduce
new risk (mcq-017, maps to COSHH Schedule 2A principle (h)); applying/repairing the hierarchy
(rsn-007, rsn-008).

**Currency caveat:** the five-tier hierarchy is stable and shared across HSE, NIOSH, OSHA and ISO
45001; the number of presented tiers varies by source but elimination is always first and PPE
always last. The COSHH **eight principles** (unranked) are distinct from the **ranked hierarchy** —
this distinction is deliberately tested (mcq-011 vs the hierarchy items).

---

## 7. Flammable-liquids storage/handling guidance (supporting context)

| Item | Reference | URL |
|---|---|---|
| Storage in containers | HSG51 (3rd edition, 2015) | https://www.hse.gov.uk/pubns/books/hsg51.htm |
| Safe use and handling | HSG140 (2nd edition) | https://www.hse.gov.uk/pubns/books/hsg140.htm |
| Storage in tanks | HSG176 (2nd edition, 2015) | https://www.hse.gov.uk/pubns/books/hsg176.htm |

**Supports:** background for the flammable-liquid DSEAR scenarios (mcq-009, rsn-003) at concept
level only — ignition-source control, containment/bunding, minimising quantities. **No
separation-distance numbers or operational parameters are used or rewarded** (defensive scope).

---

## 8. Process-safety methods — HAZOP and LOPA (concept level)

| Item | Reference | URL |
|---|---|---|
| HAZOP / LOPA / IPL concepts | Standard process-safety literature; LOPA links to IEC 61511 (SIL) for safety instrumented functions | (concept-level; IEC 61511 referenced for SIL context) |

**Supports:** HAZOP guideword purpose (mcq-022); IPL independence criteria (mcq-023, rsn-012);
prevention-vs-mitigation layers (mcq-024); HAZOP-vs-LOPA roles (mcq-025); adequacy of a single
protection layer (rsn-011).

**Currency caveat:** these are methodology concepts, not edition-bound regulations. Items are kept
strictly at **concept level** (guidewords, IPL criteria, prevention/mitigation distinction); one
rubric (rsn-011) carries an explicit auto-fail if an answer supplies operational/design detail,
to enforce the defensive scope.

---

## Cross-cutting currency watch-list (re-verify before each release)
1. **Live GB MCL list published / last-updated dates** (not an edition number) — changes ~annually
   and, post-SI 2026/484, may change without a statutory instrument. Affects mcq-002, mcq-005.
2. **GB adoption status of EU hazard classes** (ED/PBT/vPvB/PMT/vPvM) — if GB adopts any, mcq-002
   flips. Currently not adopted.
3. **Any new EH40 edition or new GB WEL.** Currently EH40/2005 4th ed. (2020) stands.
4. **CLAW 2002 / ACOP L132 amendment** (consultation closed 24 May 2026; not enacted as of June
   2026) — a watch item for mcq-010's context, though lead remains outside COSHH regardless.
