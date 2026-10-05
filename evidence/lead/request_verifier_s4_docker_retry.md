REQUEST stage=4 due=45m pin=10d2be5fa9c6

**ESCALATE closed (S4-U7):** Shared host Docker was down; Lead started Docker Desktop — engine is up on this machine now (`docker info` succeeds).

Lead withdrew **S4-C2..S4-C28** rows from the docker-stop run (**E-verifier-306..332**). **S4-C1** / **E-verifier-305** stands.

**Your turn:**
1. Re-run `powershell -NoProfile -File evidence/verifier/backfill_s4_checks.ps1` (or per-check wrappers) @ **10d2be5fa9c6**, **dirty=false**.
2. Confirm `record.py status --stage 4 --rev 10d2be5fa9c6` → **28/28** before **ACCEPT**.
3. Send **ACCEPT** or **REJECT** with product reproduction only.

UIReviewer still owns **S4-UI-C10..C13** @ pin for **S4-R28** browser scope.
