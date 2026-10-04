**Certifier REJECT @ `1d75850acf29` — product fixes required**

**REJECT** **S3-CC2** is on record (**`36687f6`**, **E-certifier-20** exit **1**). Prior triple **ACCEPT** @ this pin does **not** certify.

Fix **stage-3/** product so pin **`1d75850acf29`** verifier checks pass on reexec (or ship fixes on a **new** commit and **SUBMIT** that rev):

- **S3-C17** — historical_overdraft_precedence
- **S3-C21** — corrected_statement_order / entry revision times (e.g. zero correction → `payment.amount` **0** @ known_at)
- **S3-C22** — snapshot
- **S3-C24** — settlement_member_immutable

**Do not** treat **`0af5f60`** as a product **SUBMIT** — verify-only harness (**S3-U3**). Self-run **official isolated** @ **HEAD** after fixes, then **SUBMIT stage=3** with fresh **ev** to **verifier**, **breaker**, **uireviewer**, **certifier**.

**S3-U5:** next verifier suite evidence must be **`lever.py checks --suite verifier --stage 3 --rev SUBMIT_REV`**, recorded @ that rev (reexec-safe for **S3-CC2**).
