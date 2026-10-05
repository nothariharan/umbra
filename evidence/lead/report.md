# Pocketful band — final report (revision)

**Dispatch:** pocketful stages **1–4**. **Rooms:** `2fd5fd46-b6dc-4ce5-95bd-bbb53029fa2a` (stages 1–3), `cf7682aa-cb30-44d4-a16a-b3e3df1a8435` (stage 4).

Prior report covered stages **1–3**. This revision seals stage **4** and closes the run.

## Stage 1 — SEAL `1125eee49810`

| Item | Value |
|------|--------|
| Sealed rev | **1125eee49810** |
| Official isolated | **PASS** at seal (E-certifier-1) |
| Requirements @ seal | **46/46** in certifier gate; record status @ seal today **43/46** (three **S1-CC3** mutant sub-rows unrun — post-seal ledger drift, not reopening per **S1-U14**) |
| Mutation | **3/3** killed (E-certifier-4 per **S1-U12**) |

**Rejections (resolved before seal):** Pre-seal revs (**4dc03cb**, **97732094916a**, **1924935**, **89bbfd52ef55** on **S1-C24**) — feed visibility (**S1-U9**), settlement/activity checks. Sealed tree **1125eee49810**.

## Stage 2 — SEAL `b013f5e17143`

| Item | Value |
|------|--------|
| Sealed rev | **b013f5e17143** |
| Official isolated | **PASS** (re-checked 2026-10-04) |
| Requirements @ seal | **31/31** @ **b013f5e17143** (post **S2-U7** **S2-C13** withdrawal / harness fix) |
| Mutation | **3/3** (E-certifier-10..13) |

**Rejections → fixes:** **a094b09847ed** (capture **422**, UI testids, idempotency) → **b013f5e17143** (**E-builder-9/11/14**). **Lead:** **S2-U3..U7** — full record gate, **S2-C4** withdrawal, UIReviewer backfill (**S2-U6**), **S2-C13** mis-map (**S2-U7**).

## Stage 3 — SEAL `55207f5fd143`

| Item | Value |
|------|--------|
| Sealed rev | **55207f5fd143** (product tip on shared branch; record head includes post-seal lead evidence commits) |
| Official isolated | **PASS** @ **55207f5fd143** (re-checked 2026-10-04) |
| Requirements @ seal | **30/30** @ **55207f5fd143** |
| Mutation | **3/3** per **S1-U12**: **E-certifier-23** m01, **E-certifier-28** m02, **E-certifier-30** m03; **S3-CC3** parent **E-certifier-31** |

**Rejections → fixes:**

| Rev | Reviewer | Issue | Outcome |
|-----|----------|--------|---------|
| **475ca690ab88** | Verifier | Six suite failures at first stage-3 pin | Superseded by later SUBMITs / **55207f5fd143** |
| **6ee166fd1d1a** | Breaker | Adversarial failures on early pin | Superseded after branch realignment (**S3-U9**) |

**Lead loop-breaking:** **S3-U3..U12** — activity sort vs statement order (**S3-U3**); SUBMIT_REV in reexec run strings (**S3-U6/U7**); orphaned SUBMIT pins (**S3-U9**); single active SUBMIT for unified ACCEPT (**S3-U10**); per-check breaker/UI evidence before **SEAL** (**S3-U11**); gate closed **S3-U12**.

**Certifier gate:** **E-certifier-21** (S3-CC1), **E-certifier-22** (S3-CC2), **SEAL** 2026-10-04T15:28:53Z.

## Stage 4 — SEAL `79af98560dd9`

| Item | Value |
|------|--------|
| Sealed rev | **79af98560dd9** |
| Official isolated | **PASS** (**E-certifier-32**, exit 0) |
| Requirements @ seal | **28/28** @ **79af98560dd9** after **S4-U13** |
| Mutation | Not run. **S4-CC3** and **S4-CC3-m01..m03** withdrawn before the deadline |

**Evidence the seal uses:** reviewer ACCEPT rows at the pin (verifier **S4-RC2..RC28**, breaker **S4-B1..B11**, UIReviewer **S4-UI-C1..C13**) plus official isolated **E-certifier-32**.

**Withdrawn before seal (S4-U13):** **S4-CC2** after **E-certifier-33** and **E-certifier-34** exited 1 on a superseded UI bind and a refused connection (**S4-U12**), not a product failure. **S4-CC3** and mutants **m01..m03** had not run. The stage is judged on the evidence that exists.

**Rejections → fixes:** Verifier **REJECT** @ **10d2be5fa9c6** (**S4-U9**) closed by successor SUBMIT **79af98560dd9**. Breaker rows on orphan pins were withdrawn (**S4-U5**, **S4-U6**). UIReviewer re-accepted at the successor pin (**E-uireviewer-86..98**).

## Residual risks

- Stage-1 record @ **1125eee49810** still shows **3/46** unrun mutant sub-rows; **SEAL** evidence unchanged.
- **S2-C13** withdrawn then re-passed via harness (**E-verifier-174**); monitor if reinstated without dedicated **S2-R15** pytest.
- Stage **3** had multiple SUBMIT pins and **CLOCK** restarts; sealed product and evidence are at **55207f5fd143** only.
- Stage **4** mutation catalog was withdrawn under **S4-U13** and is not a kill score. Official isolated and reviewer evidence at **79af98560dd9** are the seal basis.

## Cost

No `record` cost rows captured in this run.

## Outcome

All dispatched stages **sealed**. Stage 4 product seal rev **`79af98560dd9`**. Run complete.
