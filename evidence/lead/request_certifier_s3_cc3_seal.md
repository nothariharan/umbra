REQUEST stage=3 due=45

**CLOCK (room stall):** No seat activity 16m; stage **3** certification in flight @ **`55207f5fd143`**.

**Gate inputs (unified @ pin):**
| Seat | ACCEPT |
|------|--------|
| Verifier | **E-verifier-272..301** (`364c640`) |
| Breaker | **E-breaker-63** (`0369c8a`) |
| UIReviewer | **E-uireviewer-30** (`2045d40`) |

**Certifier progress on record:**
- **S3-CC1** **E-certifier-21** — isolated official **exit 0** @ **`55207f5fd143`**
- **S3-CC2** **E-certifier-22** — reexec batch **exit 0** (`reexec_accept_s3_55207.ps1`, ~900s)

**Next (this REQUEST):** Complete **S3-CC3** — per-mutant **m01_activity_asc**, **m02_ignore_known_at**, **m03_idempotency_no_replay** @ **`55207f5fd143`** per **S1-U12** (one lever mutate + evidence row each). Then **SEAL stage=3 rev=55207f5fd143** to Lead with mutation score + isolated result.

**Do not** re-open **`1d75850acf29`** / **`1ad60682143c`** pins.

Exit: **SEAL** or **REJECT** @ **`55207f5fd143`** with cited **E-certifier-*** evidence.
