REQUEST stage=4 due=45

**ESCALATE answered (S4-U12 @ `79af98560dd9`).**

**E-certifier-32 / S4-CC1:** stands — no rework.

**E-certifier-33 / S4-CC2:** failure is **superseded-evidence bind**, not product. **E-uireviewer-66** is on an **earlier** UI **ACCEPT** @ the same pin; **S4-U11** + latest UI **ACCEPT** (**`5892579`**, **E-uireviewer-86..98**) is the only UI set for **S4-CC2**. Divergence on **66** does **not** require UIReviewer re-run or Builder change.

**Certifier action:**
1. Set **`reexec_accept_s4_79af985.ps1`** UI block to **E-uireviewer-86..98** (verifier **437/438**, breaker **83..93** unchanged).
2. Record **new** **S4-CC2** evidence (full batch exit 0). **E-certifier-33** remains failed audit row; do not SEAL on it.
3. **E-breaker-84:** if one reexec flakes (401) and **immediate** retry **REPRODUCED**, count CC2 pass — optional note in run string.
4. **S4-CC3** + **m01..m03**, then **SEAL** when **`record.py status --stage 4 --rev 79af98560dd9` → 28/28**.

**Pin:** **`79af98560dd9`**. Reviewer seats hold.
