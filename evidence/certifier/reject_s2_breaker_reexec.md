REJECT stage=2 rev=b013f5e17143 check=S2-CC2

ACCEPT evidence re-execution at b013f5e17143: all cited E-verifier-53..60 and E-uireviewer-6..11 reproduced (exit 0). Breaker cited runs embed a dead session port.

Command: python scripts/lever.py reexec --evidence E-breaker-21
Recorded exit: 0
Re-executed exit: 1 (twice)
Cause: recorded run pins BASE_URL=http://127.0.0.1:50489; httpx connection refused on all attacks/stage-2/test_capture.py cases.

Same pin appears on E-breaker-21,22,23,24,25,27. Re-record each S2-B* evidence at rev b013f5e17143 through record.py with a lever-booted BASE_URL (or python scripts/lever.py checks --suite breaker --stage 2 --rev b013f5e17143 scoped to the file), then send a new ACCEPT naming only the fresh evidence ids.

Certifier evidence: E-certifier-7 isolated official exit 0; E-certifier-8 reexec batch exit 1.
