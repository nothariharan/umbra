REQUEST stage=3 req=S3-R2,S3-R28 rev=1d75850acf29 due=45

ESCALATE triage (Builder @ 1d75850acf29): S3-CC2 failed on E-verifier-243 reexec only — harness gap, not product. Official isolated PASS; root cause is run_s3_pytest.ps1 / run_s3_check.ps1 default SUBMIT_REV 475ca690ab88 while lever.py reexec does not inject evidence rev (S3-U5, S3-U7 recorded).

Re-record at pin 1d75850acf29 with SUBMIT_REV embedded in every affected run string (S3-U7 pattern). Minimum set for certifier batch evidence/certifier/reexec_accept_s3_1d758.ps1:
- E-verifier-243 (full workspace suite verify/stage-3)
- E-verifier-244 through E-verifier-271 (each run_s3_check.ps1 -Check S3-C*)

Keep E-verifier-240 as-is (--rev in lever command). Self-check: `python scripts/lever.py reexec --evidence <new-id>` exit 0 for E-243 and spot-check C17/C21/C22/C24 before ACCEPT.

Exit: fresh ACCEPT stage=3 rev=1d75850acf29 citing only reexec-safe evidence; message Certifier to retry S3-CC2 (same script) once ACCEPT lands. No new Builder SUBMIT.
