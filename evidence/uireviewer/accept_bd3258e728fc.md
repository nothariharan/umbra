ACCEPT stage=2 rev=bd3258e728fc ev=E-uireviewer-4 check=S2-UI-C9

Independent run: `python scripts/lever.py checks --suite uireviewer --stage 2 --rev bd3258e728fc` → **72/72 pass** (375px + 1280px). Authorizations route shows authorize form testids, wallet-available headline, holds, capture/void controls, and error surfaces per **S2-R28** / **S2-R29** browser checks.

Evidence: `evidence/uireviewer/E-uireviewer-4.log` (exit 0, sha `96e161b6522dc7ee`).

**Note:** **S2-R22/R23** are API capture-validation scope (Verifier/Breaker). **S2-R8** pay-form idempotency is still not in the uireviewer suite; prior Verifier **E-verifier-52** on `06169d25b4fb` was not re-run for this SUBMIT.
