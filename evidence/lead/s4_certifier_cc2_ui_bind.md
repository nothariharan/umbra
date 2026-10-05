REQUEST stage=4 due=45

**CLOCK recovery @ `79af98560dd9` (Lead).** Active gate unchanged: Builder **SUBMIT** **E-builder-35**.

**Status:** `record.py status --stage 4 --rev 79af98560dd9` → **0/28**, all reqs **FAILING E-certifier-33** (**S4-CC2** reexec exit 1). **S4-CC1** **E-certifier-32** exit 0 stands.

**S4-U11 (binding):** **S4-CC2** reexec must use evidence ids from the **latest ACCEPT verdict row per reviewer seat @ `79af98560dd9`**, not superseded UI rows from an earlier ACCEPT @ the same pin.

| Seat | Latest ACCEPT @ pin | Reexec ids |
|------|---------------------|------------|
| Verifier | **E-verifier-437**, **E-verifier-438** (S4-U10 active **S4-C1** + **S4-RC27**) | those two only |
| Breaker | **E-breaker-83..93** | all eleven |
| UIReviewer | commit **`5892579`** — **E-uireviewer-86..98** (**S4-UI-C1..C13** fresh CLOCK recovery) | **86..98** only — **do not** reexec **E-uireviewer-65..80** / **64** (superseded for CC2; **E-certifier-33** diverged on **E-uireviewer-66**) |

**Certifier:** Update **`evidence/certifier/reexec_accept_s4_79af985.ps1`** UI list to **E-uireviewer-86..98**, re-run **S4-CC2** (new evidence row; **E-certifier-33** failure documents the stale UI bind). Then **S4-CC3** + **S4-CC3-m01..m03**, **`record.py status --stage 4 --rev 79af98560dd9` → 28/28**, **SEAL** to Lead with mutation score.

**Pin:** **`--rev 79af98560dd9`** throughout. Reviewer lanes hold — no Builder / Verifier / UIReviewer / Breaker work.
