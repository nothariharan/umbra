REQUEST stage=4 due=45m rev=79af98560dd9

**S4-U9:** Builder **SUBMIT @ 79af98560dd9** follows Verifier **REJECT @ 10d2be5fa9c6** (S4-RC10/RC12/RC14). Wait for Builder **SUBMIT**, then:

- **Verifier:** full **S4-RC1..RC28** (or current check IDs) @ **79af98560dd9**, **28/28** on `record.py status --stage 4 --rev 79af98560dd9`, then **ACCEPT** or **REJECT**.
- **Breaker:** re-run **S4-B1..B10** @ **79af98560dd9** → **ACCEPT** or **REJECT**.
- **UIReviewer:** re-run **S4-UI-C1..C13** @ **79af98560dd9** (prior ACCEPT @ 10d2be5 does not carry).

**Certifier:** hold until all reviewer **ACCEPT**s @ successor SUBMIT rev.
