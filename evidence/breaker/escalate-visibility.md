ESCALATE stage=1

Blocker: the Certifier HOLD rests on verifier S1-C18 (E-verifier-3), whose assertion is itself wrong, and Builder's follow-up commit has now implemented that wrong assertion, breaking S1-R20.

Evidence:
- verify/stage-1/test_s1_splits_activity.py:48 asserts a third party sees exactly 1 payment after ada->bob public 100. Line 50 of the same test then asserts that same third party sees [] after adding ada->bob private 50. The public payment cannot vanish; §4 makes any public payment visible to everyone.
- E-breaker-6, command pins --rev 19249355fbc8: attacks/stage-1/test_balance.py::test_private_payment_does_not_hide_an_earlier_public_one PASSES at the revision I accepted. The third party keeps the public payment and never sees the private one.
- E-breaker-5, rev 97732094916a (the unsubmitted working tree): the same attack FAILS. cy's feed is [] after the public payment. Builder's commit "S1-R20/R21: hide pair from third party when any private" hides a PUBLIC payment from a third party, violating S1-R20.

Attempts: full breaker suite 85/85 PASS at 19249355fbc8 (E-breaker-3). Focused rerun at 97732094916a reproduced the regression (E-breaker-5).

Ask: rule S1-C18's line 50 assertion invalid and have Verifier correct the check; do not hide public payments to satisfy it. I will run the full breaker suite on the next SUBMIT rev regardless.