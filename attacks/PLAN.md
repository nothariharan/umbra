# Breaker attack plan — Pocketful stage 1

Suite: `attacks/stage-1/`, run by `python scripts/lever.py checks --suite breaker --stage 1`.
Every test reads `BASE_URL`; the lever builds and boots the exact revision.

## Threat model

The service keeps one mutable ledger behind an HTTP API. The interesting ways it
breaks are: a check-then-act race that overdraws a wallet, an operation applied
twice (or zero times) under retry, a settlement that commits only half a batch, and
state that does not survive export/import. All tests assume the implementation is
wrong and try to prove it.

## Classes and coverage

| Class | File | Headline attacks |
|---|---|---|
| Concurrency | `test_concurrency.py` | 50 simultaneous debits of a limited balance (overspend), same-key stampede, one request paid 30 ways (pay-once), two settlements draining one wallet, 60 mixed payments conserved, 50 in-flight reads |
| Repetition/ordering | `test_idempotency.py` | missing/empty/oversize key, replay identity, changed-body 409, 4xx key reuse, claimed key beats invalid body, path/user scoping, decline/cancel twice, split/settlement replay |
| Balance/conservation | `test_balance.py` | exact drain then block, failed pay leaves no trace, request exceeding balance, short pay then fund and pay, negative-fixture reset, feed visibility, note verbatim and length, amount forms and range, ±2⁵³ exactness, minor_units |
| Request lifecycle | `test_requests.py` | wrong-party pay/decline/cancel 403, unknown 404, decline/cancel after terminal 409, replay body must be identical, direction/status filters, newest first, has_more, visibility, auth required |
| Boundaries | `test_boundaries.py` | split rounding table and order, zero-share request, sole-caller split, pagination bounds and bad integer query forms, signup handle derivation/truncation/conflicts, bad tokens |
| Settlements | `test_settlement.py` | collective net-zero batch on empty wallets (must commit), collective insufficiency is atomic, entry-error precedence, batch size 1/32/33, response order and linkage, operator permissions do not leak private data |
| Durability | `test_durability.py` | export shape, round trip preserves balances/tokens/receipts/timestamps, repeated import idempotent, read-only snapshot, invalid import 422 unchanged, reset clears imported state, export/import preserves operator permission |

## Reproduction

```
python scripts/lever.py checks --suite breaker --stage 1 --rev <REV>
```

A failing test that reproduces twice is a REJECT; the protocol line names the class,
the command, its exit code and the output hash.

# Breaker attack plan — Pocketful stage 2

Suite: `attacks/stage-2/`, run by `python scripts/lever.py checks --suite breaker --stage 2`
(which also re-runs `attacks/stage-1`). Every test reads `BASE_URL`; the lever builds and
boots the exact revision.

## Threat model

Stage 2 adds money that is reserved but not moved. The ways it breaks are: a hold that is
counted as spendable, a capture that exceeds its authorization or runs twice, a capture/void
or capture/expiry race that both moves and releases the same money, an expiry that only
happens when a request touches the deadline, wallet fields that disagree, and a browser that
lets a stale read win, double-pays an unchanged form, or mistreats a lost response as a
refusal.

## Classes and coverage

| Class | File | Headline attacks |
|---|---|---|
| Holds / wallet | `test_holds.py` | `/me` total/available/held; hold moves no money; idempotent authorize and key reuse; holds absent from the feed; `insufficient_funds` judged on available; self_payment and validation; seeded-hold derivation and over-balance reset 422; TTL default/custom/invalid; seeded and clock expiry |
| Capture / void | `test_capture.py` | full and partial final capture release the remainder; extended `final:false` keeps it; cumulative `captured_amount`/`payment_ids`/`remaining_amount`; over-remaining 422; byte-exact replay body; idempotent capture; receiver-only capture, payer-only void; expired/voided/closed errors; list scope, filters and pagination |
| Concurrency | `test_concurrency2.py` | 24-way full-capture stampede moves money once; 30-way partial captures never exceed the authorized amount; 40-way holds never overspend available; payment/hold race; capture/void race is serialisable; total and non-negative available at every read under mixed load |
| Content negotiation | `test_ui_api.py` | required routes reachable; `/requests` and `/authorizations` serve HTML vs JSON by `Accept`; JSON endpoints unaffected by a text/html `Accept` |
| UI races | `test_ui_race.py` | unchanged pay-form resubmit does not double-pay; lost response shows `pay-uncertain` then one-money retry; remote spend shows `pay-error` and refreshes with inputs kept; remote cancel drops the stale pay button; post-action list refresh; `wallet-refresh` latest-wins over a delayed read; authorization testids, available headline and permitted capture/void controls |
| Upgrade | `test_upgrade.py` | a stage-1-shaped export imports; the session survives; pending requests stay payable; a lost payment retries to the original payment; a hold survives a snapshot and stays capturable |

## Reproduction

```
python scripts/lever.py checks --suite breaker --stage 2 --rev <REV>
```

A failing test that reproduces twice is a REJECT; the protocol line names the class,
the command, its exit code and the output hash. UI races run Chromium headless inside the
same suite; a browser launch failure is a real failure, not a skip.
