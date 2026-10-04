REQUEST stage=3 req=S3-R27,S3-R29 due=45

ESCALATE (breaker): SUBMIT rev 1ad60682143c is not ancestor of HEAD; record.py head() is 5645514c4daf (last stage-* commit). E-breaker-62 proves fix at 1ad60682143c via lever --rev; verdict ACCEPT cannot stamp at 1ad60682143c until product history aligns (S3-U9).

Land S3-R17/R27 correction ordering (and any other stage-3 deltas you intend to seal) as a new commit on current main touching stage-3/, so git log -1 -- stage-* equals your SUBMIT rev. Do not SUBMIT an orphaned rev. After commit: isolated official ev, then SUBMIT that rev to all four seats.

Exit: one SUBMIT rev R with merge-base --is-ancestor R HEAD and head()==R for stage-*.
