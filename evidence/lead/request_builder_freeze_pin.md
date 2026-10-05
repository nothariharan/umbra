REQUEST stage=4 due=15m pin=10d2be5fa9c6

**S4-U8:** Product **HEAD** moved (`79af985`, `2401ba6`, **E-builder-35**) during the open gate @ **10d2be5fa9c6**. Those commits are **out of scope** until this SUBMIT closes (**SEAL** or **REJECT** at pin).

**Stop** new `stage-4/` product commits on `main` until **Certifier SEAL** @ pin or a **REJECT** forces a new SUBMIT. Hold **E-builder-33** SUBMIT; do **not** send a new SUBMIT for orphan HEADs.

If you already committed fixes needed for stage 4, leave them on record but **do not** advance the active gate; Lead will reopen only after the pin gate completes or fails closed.
