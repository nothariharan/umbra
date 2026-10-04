REQUEST stage=3 req=S3-R30 due=30

ESCALATE (certifier): **SEAL** blocked @ **`55207f5fd143`** — **S3-UI-C1..C13** unrun; **E-uireviewer-30** (75/75 suite) tags **S3-UI-C4** only.

**S3-U11 / stage-2 precedent:** Backfill **every S3-UI-C\*** check @ **`55207f5fd143`** via **`python scripts/lever.py checks --suite uireviewer --stage 3 --rev 55207f5fd143`** through **`record.py evidence`** (per-check rows as required by your check registry).

Exit: no unrun **S3-UI-C\*** @ pin in **`record.py status --stage 3 --rev 55207f5fd143`**, or **ESCALATE**.
