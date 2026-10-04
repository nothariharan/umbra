# Pocketful band — final report

**Dispatch:** pocketful stages **1–2** (payments → authorizations/holds). **Room:** `2fd5fd46-b6dc-4ce5-95bd-bbb53029fa2a`.

## Stage 1 — SEAL `1125eee49810`

| Item | Value |
|------|--------|
| Sealed rev | **1125eee49810** |
| Official isolated | **PASS** at seal (E-certifier-1) |
| Requirements @ seal | **46/46** verified in certifier gate; record status @ seal today shows **43/46** (three **S1-CC3** mutant sub-check rows unrun — post-seal ledger drift, not reopening gate per **S1-U14**) |
| Mutation | **3/3** killed (E-certifier-4 per **S1-U12** per-mutant policy) |

**Rejections (resolved before seal):** Verifier/Breaker REJECTs on pre-seal revs (e.g. **4dc03cb**, **97732094916a**, **1924935**) — feed visibility (**S1-U9**), settlement/activity checks. Final sealed tree at **1125eee49810**.

## Stage 2 — SEAL `b013f5e17143`

| Item | Value |
|------|--------|
| Sealed rev | **b013f5e17143** |
| Official isolated | **PASS** (re-checked 2026-10-04, exit 0) |
| Requirements @ seal | **31/31** @ **b013f5e17143** (post **S2-U7** **S2-C13** withdrawal / harness fix) |
| Mutation | **3/3** (E-certifier-10..13) |

**Rejections → fixes:**

| Rev | Reviewer | Issue | Outcome |
|-----|----------|--------|---------|
| **a094b09847ed** | Verifier/Breaker/UIReviewer | Login chrome, pay idempotency, capture **422**, UI testids | Superseded by **b013f5e17143** (Builder **E-builder-9/11/14**) |
| **a094b09847ed** | Verifier | **S2-C19** invalid capture amount → **201** | Fixed capture validation + authorize UI |
| **89bbfd52ef55** | Verifier | **S1-C24** wrong error code on stale pin | Rejected pin; fix lives in sealed stage-1 rev |

**Lead loop-breaking:** **S2-U3..U7** — full **31/31** record gate for **SEAL**; certifier hold; **S2-C4** withdrawal; UIReviewer multi-turn backfill (**S2-U6**); **S2-C13** mis-map (**S2-U7**).

## Residual risks

- **S2-C13** check withdrawn then verifier re-passed via updated harness (**E-verifier-174**); competing-client UI remains covered by official + breaker suites at seal rev — monitor if **S2-C13** is reinstated without dedicated **S2-R15** pytest.
- Stage-1 record view @ **1125eee49810** shows **3/46** unrun mutant sub-rows; certifier **SEAL** evidence remains valid.
- Runtime **CLOCK** restarts caused duplicate recovery traffic; no product impact on sealed revs.

## Cost

No `record` cost rows captured in this run.

## Outcome

Both dispatched stages **sealed**. Product head **`b013f5e17143`**. No stage **3** in spec/repo — run complete.
