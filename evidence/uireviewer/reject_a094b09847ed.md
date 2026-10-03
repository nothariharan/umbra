REJECT stage=2 rev=a094b09847ed check=S2-UI-C4 ev=E-uireviewer-1

**S2-R6 (Auth UI):** After valid login, the browser stays on `/login` and never renders `current-user`, `current-handle`, or `logout-button` at **375px** (same class of failure at 1280px).

**S2-R4 / S2-R7:** Home missing mandated testids including `request-handle`, `request-*`, `activity-list`, `wallet-refresh` (`test_s2_ui_r4_home_mandated_testids`).

**S2-R10 / S2-R11:** No `empty-activity` / `activity-item-*`; requests screen missing `empty-requests`, `incoming-list`, `outgoing-list`.

**S2-R28 / S2-R29:** `/authorizations` missing `authorize-handle` and related authorize form testids; hold/capture/void flows untestable in browser.

Screenshot: `review/stage-2/screenshots/reject_s2_r6_no_current_user_375px.png` (post-submit click, URL still `/login`).

Reproduction:
```
python scripts/lever.py checks --suite uireviewer --stage 2 --rev a094b09847ed
```
Exit **1**. Output sha **see E-uireviewer-1** (`record/uireviewer.jsonl`).

Full suite at this rev: **30 failed, 42 passed** (72 tests). Root cause: login/session chrome and incomplete mandated `data-testid` wiring in `stage-2/web/` + client JS.
