ESCALATE response stage=1

**Ruling:** Breaker is correct. §4 feed contract is **per payment**: third party **cy** must see **exactly one** payment after ada→bob **public** 100 + **private** 50 (the public receipt only). `test_s1_c18_activity_visibility` **line 50** (`payments == []`) is **invalid** and contradicted S1-R20.

**Record:** **S1-U9**, **S1-U10**; **S1-C18 withdrawn** until Verifier fixes the test (expect `len==1`, public payment present, no private payment id for cy).

**Verifier** — REQUEST due=20: Fix `verify/stage-1/test_s1_splits_activity.py` per S1-U9; re-register **S1-C18** (or new id) mapped to S1-R20/R21/R39; add repro that fails if a **public** payment is hidden from a third party. Re-evaluate **4dc03cb** REJECT only against the **corrected** check (private visible to cy still fails; passing corrected check voids that REJECT basis).

**Builder** — Revert **pair-hiding** (`9773209` / "hide pair from third party when any private"). Filter **per payment**: public → all callers; private → sender and receiver only. **SUBMIT** new rev when official + self-run pass.

**Breaker** — Hold full suite on next **SUBMIT** rev as stated.

**Certifier** — HOLD on S1-C18/E-verifier-3 until Verifier republishes corrected check and evidence.
