REJECT stage=1 rev=4dc03cb70c11 check=S1-B8

Two attacks fail on your submitted revision and each has failed twice (a full-suite run and a focused run).

1) Class: repetition/ordering. S1-R34/S1-R35.
Attack: once a request is paid, POST /requests/{id}/pay with a NEW Idempotency-Key must return 409 request_not_pending. Yours returns 200 carrying the existing payment. Only the identical key may replay as 200.
Repro: attacks/stage-1/test_idempotency.py::test_request_pay_replay_after_paid_returns_200
       attacks/stage-1/test_concurrency.py::test_concurrent_pay_request_moves_money_once

2) Class: boundaries. S1-R42.
Attack: POST /settlements whose transfers is not a list is a malformed batch shape; §11 says 422 validation_failed. Yours returns 400 malformed_request.
Repro: attacks/stage-1/test_settlement.py::test_malformed_batch_shapes_are_422

Recorded: E-breaker-2, rev 4dc03cb70c11, exit 1, output sha256 2200382a5ecba789, log evidence/breaker/E-breaker-2.log.
Exact recorded command:
C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider attacks/stage-1/test_idempotency.py::test_request_pay_replay_after_paid_returns_200 attacks/stage-1/test_settlement.py::test_malformed_batch_shapes_are_422
Canonical suite command (exit 1 until fixed): python scripts/lever.py checks --suite breaker --stage 1

Fix these and SUBMIT again; the rest of the suite passed at this revision.