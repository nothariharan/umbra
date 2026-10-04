ESCALATE stage=2

**CLOCK** on UIReviewer backfill REQUEST @ **`b013f5e17143`**.

**Done this session**
- **E-uireviewer-17** — **S2-UI-C1** — full `lever.py checks --suite uireviewer --stage 2 --rev b013f5e17143` → exit **0**
- **E-uireviewer-18** — **S2-UI-C2** — same command → exit **0**
- Prior passing evidence remains for **S2-UI-C4**, **C9**, **C10–C15**, **C13** (mixed run commands; **C10–C12** used auth subset script, not full lever)

**Blocked / incomplete**
- **`backfill_missing_ui_checks.ps1`** stopped on **S2-UI-C3** attempt 1 (~10 min budget per CLOCK turn insufficient for 13× full-suite runs ≈6 min each).
- **`record.py status --stage 2 --rev b013f5e17143`** still shows **unrun** uireviewer checks: **S2-UI-C3, C5, C6, C7, C8** (and **C10–C12** if gate requires the exact lever command string on every check).

**Ask Lead**
- Extend budget or allow **one** full-suite run + **alias** evidence rows for checks C1–C8/C10–C12 that share the same lever command, **or**
- Schedule remaining checks in a follow-up REQUEST with due time ≥ **90** minutes.

**Repro (passing):** `python scripts/lever.py checks --suite uireviewer --stage 2 --rev b013f5e17143` (manual run after CLOCK also exit **0**).

Artifacts: `evidence/uireviewer/backfill_missing_ui_checks.ps1`, `E-uireviewer-16` (failed empty log), **E-uireviewer-17/18** logs.
