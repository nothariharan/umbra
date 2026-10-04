REQUEST stage=2 req=all due=30

Backfill stage-2 UIReviewer evidence at SUBMIT rev **b013f5e17143**.

1. For **every** registered **S2-UI-C\*** check, record passing evidence at **`--rev b013f5e17143`** via **`python scripts/lever.py checks --suite uireviewer --stage 2 --rev b013f5e17143`** through **`record.py evidence`** (include **E-uireviewer-13…15** if already run — commit if missing).
2. **`python scripts/record.py status --stage 2 --rev b013f5e17143`** must show **no unrun** uireviewer-owned checks before stage gate clears.

Exit: UI checks mapped to requirements at **b013f5e17143**, or **ESCALATE** with blocker.
