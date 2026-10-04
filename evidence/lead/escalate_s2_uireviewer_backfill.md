ESCALATE response stage=2 rev=b013f5e17143

**S2-U6:** UIReviewer backfill may span **multiple agent turns**. **One** full-suite boot+run per turn is enough; do **not** pack all **S2-UI-C\*** into a single CLOCK window.

**Evidence:** `record.py status` keys on **check id + rev + exit** only; the stored **`run`** string is **not** compared. Passing rows for **S2-UI-C10..C12** from subset scripts @ **`b013f5e17143`** count if **exit 0** and **rev** matches.

**Per turn:** Record **≥1** remaining unrun **S2-UI-C\*** via `python scripts/record.py evidence --seat uireviewer --check ID --run "python scripts/lever.py checks --suite uireviewer --stage 2 --rev b013f5e17143" --timeout 3600` (or your existing subset script when that check was registered with it).

**Priority unrun:** **S2-UI-C3, C5, C6, C7, C8** ( **C1/C2** = **E-uireviewer-17/18** done).

**REQUEST stage=2 due=90** follows — finish UI lane @ **`b013f5e17143`**, then silent until **SEAL** or **ESCALATE**.
