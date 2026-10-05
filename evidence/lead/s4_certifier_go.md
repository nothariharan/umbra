REQUEST stage=4 due=45

**SUBMIT pin:** `79af98560dd9` (**E-builder-35** official isolated). **S4-U9** successor SUBMIT; **S4-U10** active verifier suite **S4-C1** + **S4-RC27** only (**S4-RC2..RC26**, **S4-RC28** withdrawn). **`10d2be5fa9c6`** closed.

**Reviewer ACCEPT @ pin (binding cites):**
- **Verifier:** **E-verifier-437**, **E-verifier-438** (**S4-U10**; prior **E-409..436** historical only)
- **Breaker:** **E-breaker-83..93** (incl. **S4-B11** / **E-breaker-92**)
- **UIReviewer:** **E-uireviewer-65..80**, **E-uireviewer-64** (**S4-UI-C1..C13**)

**Certifier:** Run **S4-CC1** (hermetic isolated official), **S4-CC2** (reexec every evidence id on the ACCEPT verdicts above), **S4-CC3** + **S4-CC3-m01..m03** mutants per **S1-U12**, then **SEAL** to Lead with mutation score. Pin **`--rev 79af98560dd9`** throughout.
