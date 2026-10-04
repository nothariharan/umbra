ESCALATE stage=2 rev=b013f5e17143 — **S2-U7** decided.

**S2-C13** must exercise **S2-R15** (competing clients: **pay-error** + balance refresh, stale pay control after remote cancel, **pay-uncertain** on lost response with same idempotency retry). Running **`test_s2_c6_pay_form_no_double_submit_without_change`** under **S2-C13** is **invalid evidence** (that test belongs to **S2-C6** / **S2-R7–R8**).

**Verifier:** add or wire a **verify/stage-2** test (e.g. **`test_s2_c13_*`**) covering **S2-R15** UI behaviors; update **`run_s2_check.ps1`** **S2-C13** branch to that node only. Record passing **`record.py evidence`** @ **`b013f5e17143`**. Product pin unchanged unless a **REJECT** repro appears.

**Withdrawn:** failing **S2-C13** rows **E-verifier-156/172/173** (mis-map). **Certifier:** hold **SEAL** until **31/31**.

REQUEST stage=2 req=S2-R15 due=45 — exit **31/31** @ **b013f5e17143** or **ESCALATE** with one blocker.
