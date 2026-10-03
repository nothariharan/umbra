CLOCK response stage=2

**Status** (`record.py status`, rev **a094b09847ed**): **0/31** verified. **Verifier REJECT** (E-verifier-47: S2-R6 login/`current-user`, S2-R8 pay double-submit). **Breaker REJECT** (E-breaker-20: auth UI). **UIReviewer REJECT** (E-uireviewer-1: S2-R6/R4/R7/R10/R11/R28/R29). Official isolated passed (E-verifier-48) but does not clear UI/auth failures.

**REQUEST due=45 → Builder:** Fix REJECT findings on **a094b09847ed** (signed-in shell after login; pay form must not debit on unchanged resubmit; authorization UI testids/flows). **SUBMIT** new **rev** with self-run official isolated + evidence. Use current `verify/` (**s2lib** fix at **79f3ec7123c3**).

**Verifier / Breaker / UIReviewer / Certifier:** Hold until new **SUBMIT**. Re-run at pinned **`--rev`** only.
