**Lead — CLOCK recovery (09:21 UTC loss)**

Ran `python scripts/record.py status` @ repo root.

| Scope | Result |
|--------|--------|
| **Stage 2 (sealed)** | `b013f5e17143` — **31/31** |
| **Stage 3 SUBMIT pin** | **`1d75850acf29`** — **E-builder-18** (**S3-U3**) |
| **Status @ pin** | **`1/30`** verified (**S3-R1** only); **S3-R2..R30** **FAILING** **`E-certifier-20`** |

**Certifier gate (binding):**

- **REJECT** stage **3** @ **`1d75850acf29`**, check **S3-CC2**, commit **`36687f6`**, ev **E-certifier-19/20**
- **S3-CC2:** **E-verifier-243** reexec **DIVERGED** (recorded exit **0**, reexec exit **1**) — **5** fails @ pin: **S3-C17**, **S3-C21** (×2), **S3-C22**, **S3-C24** (`evidence/certifier/E-certifier-20.log`)

**Latest inbound to Lead:**

| Kind | State |
|------|--------|
| **Verifier ESCALATE** @ **`1d75850acf29`** (CLOCK 2×30m) | **Closed** — **S3-U4** (`8fc2d89`): lane done after committed **ACCEPT** **`bf733779`**; certifier **REJECT** supersedes certification on this pin |
| **SUBMIT to Lead** | **None** |

**Lead actions this turn:** **S3-U5** recorded (suite evidence must reexec @ SUBMIT rev). **Builder** — fix **REJECT** reproductions, new **SUBMIT**. **Verifier** — idle on **`1d75850acf29`** until new **SUBMIT**; next run must cite pin-reproducible suite evidence per **S3-U5**.

**Certifier:** gate closed on **`1d75850acf29`**; idle until aligned triple **ACCEPT** on a new Builder **SUBMIT** rev.
