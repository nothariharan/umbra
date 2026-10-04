REQUEST stage=2 req=all due=30

Backfill stage-2 verifier evidence at SUBMIT rev **b013f5e17143**.

1. For **every** registered **S2-C\*** check mapped in the record, run **`python scripts/record.py evidence`** with **`--rev b013f5e17143`** (lever boot/checks pinned). Prefer **`python scripts/lever.py checks --suite verifier --stage 2 --rev b013f5e17143`** split per check if the suite driver supports it; otherwise one full suite row for **S2-C4** must **exit 0** and supersede withdrawn **E-verifier-135**.
2. **`python scripts/record.py status --stage 2 --rev b013f5e17143`** must show **no FAILING** and **no unrun** verifier-owned checks before you **ACCEPT** (full stage scope) or go silent if already ACCEPT on record and only backfilling.
3. Do **not** REJECT **b013f5e17143** on stale **`a094b09847ed`** pins.

Exit: status shows verifier checks contributing to **31/31** at **b013f5e17143**, or **ESCALATE** with one named blocker.
