ACCEPT stage=2 rev=b013f5e17143 ev=E-uireviewer-8,E-uireviewer-9

Consolidated SUBMIT re-run @ pinned **`b013f5e17143`**:

| Evidence | Check | Result |
|---|---|---|
| **E-uireviewer-8** | S2-UI-C4 (+ full suite) | `lever.py checks --suite uireviewer --stage 2 --rev b013f5e17143` → **72/72 pass** |
| **E-uireviewer-9** | S2-UI-C13 | `evidence/uireviewer/repro_s2_r8.ps1` → exit **0** (**S2-R8**) |

Covers browser scope **S2-R4, R6, R7, R10, R11, R28, R29** via Playwright suite; **S2-R22/R23** are API (Verifier). **S2-UI-C13** also in repo for future lever exports that include `test_s2_ui_r8_pay_idempotency.py`.
