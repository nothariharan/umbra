REQUEST stage=4 due=45m pin=10d2be5fa9c6

After Builder **SUBMIT @ 10d2be5fa9c6** (or immediately if SUBMIT already in room):

1. Register missing **S4-C27** (delivery: stage-4/, Dockerfile, RUN.md, earlier stages pass) if not in record.
2. Record per-check evidence **S4-C1..S4-C28** at **rev=10d2be5fa9c6** (`git merge-base --is-ancestor 10d2be5fa9c6 HEAD` required). Use lever `--rev 10d2be5fa9c6 --isolated` for official gate.
3. Send **ACCEPT** or **REJECT** with reproduction.

`record.py status --stage 4 --rev 10d2be5fa9c6` must reach **28/28** before ACCEPT (currently **S4-R27 NO CHECK**; **S4-R28** is UIReviewer scope but S4-C28 may need your check row).

Do not git reset/checkout main off the frozen pin (S4-U4/U5).
