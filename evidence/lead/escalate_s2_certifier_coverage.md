ESCALATE response stage=2 rev=b013f5e17143

**Pin:** **`b013f5e17143`**. Builder hold unchanged — no new product commits until a seat **REJECT** or Lead **REQUEST** says otherwise.

**Scoped SEAL denied.** **S1-U13** stands: **SEAL** at SUBMIT rev requires **`record.py status --stage 2`** **31/31 verified** at that rev with per-check evidence rows, not certifier gate alone.

**Certifier lane @ `b013f5e17143`:** **E-certifier-7** (S2-CC1), **E-certifier-16** (S2-CC2 reexec), **E-certifier-10…13** (S2-CC3) satisfy the certifier gate. **Hold SEAL** until reviewer backfill clears status.

**Blockers Lead owns:**
- **S2-C4 / E-verifier-135:** withdrawn — full-suite row contradicted scoped **E-verifier-140** (S2-C19 pass) at the same rev; Verifier re-records **S2-C4** via a passing full verifier suite at **`b013f5e17143`**.
- Remaining **unrun** **S2-C\*** / **S2-UI-C\*** at this rev: narrowed **REQUEST** to Verifier and UIReviewer (30m).

**After status 31/31:** Certifier issues **SEAL stage=2 rev=b013f5e17143** citing **E-certifier-7,16,10…13** and isolated result.

**Rulings recorded:** **S2-U3, S2-U4, S2-U5**.
