SUBMIT stage=1 req=S1-R42 rev=1125eee49810 ev=E-builder-5,E-builder-13

S1-C24: settlement batch self-transfer returns 422 error.code self_payment (not validation_failed). Fixed in 4dc03cb70c11; present in sealed stage-1 rev 1125eee49810.

Repro: evidence/builder/repro_s1_c24.ps1 (S1-C24 @ 1125eee49810) pass E-builder-13. Pin 89bbfd52ef55 predates the fix.
