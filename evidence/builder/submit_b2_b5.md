SUBMIT stage=2 req=S2-R22,S2-R23,S2-R28 rev=b013f5e17143 ev=E-builder-8,E-builder-11

S2-B2: parseCaptureBody returns validation_failed (422) when amount is present but not a positive integer; no full capture on 0, -1, 1.5, or string amounts.
S2-B5: authorizations.html includes authorize-handle, authorize-amount, authorize-note, authorize-visibility, authorize-submit; wallet-held via setWallet.

Repro of E-breaker-18/20 passes at b013f5e17143. Official isolated stage 2: E-builder-11.
