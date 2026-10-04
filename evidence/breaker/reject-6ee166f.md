REJECT stage=3 rev=6ee166fd1d1a check=S3-B1,S3-B3 ev=E-breaker-48,E-breaker-50,E-breaker-52,E-breaker-53
The "activity asc" change regressed two requirements. Reproduce:
  python scripts/lever.py checks --suite breaker --stage 3 --rev 6ee166fd1d1a
exit 1.

S3-B1 attacks/stage-3/test_timestamps.py: 3 failed, 4 passed, exit 1, output sha 8f2afb76dfb9aafe (E-breaker-52; first run E-breaker-48 sha 208125cff97e674a).
  GET /activity now returns oldest-first. S1-R39 says visible payments newest first and S3-R3 says orders by created_at as before. Seeded offsets p_b=2026-09-24T11:00:00+02:00 (09:00Z), p_a=06:00Z, p_c=2026-09-24T08:00:00+05:30 (02:30Z) come back [p_c,p_a,p_b]; must be [p_b,p_a,p_c].

S3-B3 attacks/stage-3/test_statement.py: 1 failed, 11 passed, exit 1, output sha 473e620400e9733d (E-breaker-53; first run E-breaker-50 sha 57165f09b25f13cf).
  GET /statement drops the newest seeded entry. With p1@p T1, p2@T2, p3@T3 it returns [p1,p2] and omits p3, so opening_balance + sum(delta) != closing_balance. S3-R9 requires every entry, oldest-first.

Both failures reproduced twice at this revision. Restore newest-first ordering and the missing statement entry, then SUBMIT.