REJECT stage=2 rev=a094b09847ed check=S2-B2,S2-B5

Two defects, each reproduced twice against the submitted build. The service was booted
from the exact revision with `python scripts/lever.py boot --stage 2 --rev a094b09847ed`
(BASE_URL=http://127.0.0.1:58920).

1) Boundaries (S2-B2; S2-R22, S2-R23). POST /authorizations/{id}/capture treats an invalid
present amount as an omitted one and captures the whole remaining allowance. `amount` 0, -1,
1.5 and "100" each return 201 with amount 2000; the spec table requires 422 validation_failed
for an amount below 1 or not an integer. A malformed amount must not move the full allowance.

  repro:
    set BASE_URL=http://127.0.0.1:58920&& C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider attacks/stage-2/test_capture.py::test_capture_invalid_amount_is_422 & C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider attacks/stage-2/test_capture.py::test_capture_invalid_amount_is_422
  exit=1  output sha=1a602150141e03c9  evidence=E-breaker-18  log=evidence/breaker/E-breaker-18.log

2) UI / auth UI (S2-B5; S2-R28). The /authorizations screen ships no authorize form:
authorize-handle, authorize-amount, authorize-note, authorize-visibility, authorize-submit
and authorize-error are absent from the DOM. Only wallet-available, wallet-balance, wallet-held
and the authorization list render.

  repro:
    set BASE_URL=http://127.0.0.1:58920&& C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider attacks/stage-2/test_ui_race.py::test_authorizations_page_shows_available_headline_and_permitted_controls & C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider attacks/stage-2/test_ui_race.py::test_authorizations_page_shows_available_headline_and_permitted_controls
  exit=1  output sha=7ec144a162796c8d  evidence=E-breaker-20  log=evidence/breaker/E-breaker-20.log

Also failing in the full run at this revision (single run so far, not yet doubled):
pay-uncertain never appears when a POST /payments response is lost after commit; a refused
payment does not refresh wallet-balance after a remote spend; a remotely cancelled request
leaves its stale Pay button in the DOM.

Fix the two reproduced defects and resubmit one revision; I will re-run the whole suite.
