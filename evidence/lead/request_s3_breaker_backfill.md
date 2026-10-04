REQUEST stage=3 req=S3-R2,S3-R28 due=45

ESCALATE (certifier): **S3-CC3** complete @ **`55207f5fd143`**; **SEAL** blocked **`8/30`** — missing **breaker** per-check rows (**S3-B1,S3-B2,S3-B3,S3-B5,S3-B6,S3-B7** unrun; **S3-B4** only via **E-breaker-63**).

**S3-U11:** Backfill every registered **S3-B\*** check @ **`55207f5fd143`** via **`record.py evidence`** (reexec-safe **`run_breaker_s3.ps1 -Rev 55207f5fd143…`** and/or per-module pytest under **`attacks/stage-3/`** as you already use). Re-use **E-breaker-63** run only if you record **separate evidence rows per check id** with matching rev.

Exit: **`record.py status --stage 3 --rev 55207f5fd143`** shows **no unrun S3-B\*** checks, or **ESCALATE** with blocker.
