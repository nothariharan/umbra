REQUEST stage=4 due=30m pin=10d2be5fa9c6 req=S4-R28

Re-record **S4-UI-C10, S4-UI-C11, S4-UI-C12, S4-UI-C13** at product pin **10d2be5fa9c6** only:

- `python scripts/lever.py checks --suite uireviewer --stage 4 --rev 10d2be5fa9c6`
- Evidence rows must show **rev=10d2be5fa9c6**, **dirty=false** (withdraw/replace E-uireviewer-52..56 stamped b3541f195b66 per S4-U6).
- Narrow (375) and desktop (1280) as prior stage-3 UI gate.

Then **ACCEPT** stage 4 @ **10d2be5fa9c6** citing all **S4-UI-C1..C13** evidence, or **REJECT** with repro.
