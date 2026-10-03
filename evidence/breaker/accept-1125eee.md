ACCEPT stage=1 rev=1125eee49810 ev=E-breaker-7

All 86 breaker attacks pass in my own run at this revision: concurrency
(overspend, pay-once, same-key stampede, settlement drain, 50 in-flight reads),
repetition/ordering (idempotency key rules, request lifecycle, replay-after-paid,
decline/cancel repeats, split and settlement replay), balance and conservation,
boundaries (split rounding, pagination, signup handles, amount forms), settlements
(collective net-zero, entry-error precedence, batch sizes 1/32/33, operator
permissions) and export/import durability.

Evidence: E-breaker-7, exit 0, 86 passed, log evidence/breaker/E-breaker-7.log.
Command: python scripts/lever.py checks --suite breaker --stage 1 --rev 1125eee49810

Builder: the per-payment feed at this revision satisfies S1-R20/S1-R21 and the
S1-U9/S1-U10 rulings. Certifier: every reviewer's revision is 1125eee49810; the
stage is ready for the isolated re-check.
