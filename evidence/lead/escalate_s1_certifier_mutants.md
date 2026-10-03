ESCALATE response stage=1 rev=1125eee49810

**S1-CC3 — bounded mutation policy (S1-U12):** Do **not** record `lever mutate --catalog` in one evidence row. Run **one mutant per evidence row**, `--rev 1125eee49810`, `--timeout 1800` on `record.py evidence`:

1. `python scripts/lever.py mutate --stage 1 --rev 1125eee49810 --mutant mutants/stage-1/m01_pair_hide_public.patch --suites official,verifier,breaker`
2. Same for **m02**, **m03**.

Each run must end **killed** (≥1 suite). Aggregate **S1-CC3** PASS only when all three rows exit 0. Partial **E-certifier-3** (exit 124) does not count; supersede with per-mutant evidence ids.

**SEAL gate — status (S1-U13):** `record.py status --stage 1 --rev 1125eee49810` is **1/46** because most **S1-C\*** / **S1-B\*** lack owner evidence at this rev (full suite passed but not recorded per check). **SEAL will refuse** until backfilled.

**REQUEST due=30 → Verifier:** At **1125eee49810**, record passing evidence for **every** registered **S1-C\*** check (use full-suite command or per-module pytest; pin `--rev`). Exit: `status --rev 1125eee49810` shows no verifier `unrun` on any requirement you cover.

**REQUEST due=30 → Breaker:** Same for **S1-B\*** at **1125eee49810**.

**Certifier after CC3 + backfill:** Re-run `status --stage 1 --rev 1125eee49810`. If **46/46**, **SEAL** with **S1-CC1** E-certifier-1, **S1-CC2** E-certifier-2, and completed **S1-CC3** mutant evidence. Mutation score = 3/3 killed.

**Builder:** Hold.
