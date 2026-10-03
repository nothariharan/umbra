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
| Boundaries | `test_boundaries.py` | split rounding table and order, zero-share request, sole-caller split, pagination bounds and bad integer query forms, signup handle derivation/truncation/conflicts, bad tokens |
| Settlements | `test_settlement.py` | collective net-zero batch on empty wallets (must commit), collective insufficiency is atomic, entry-error precedence, batch size 1/32/33, response order and linkage, operator permissions do not leak private data |
| Durability | `test_durability.py` | export shape, round trip preserves balances/tokens/receipts/timestamps, repeated import idempotent, read-only snapshot, invalid import 422 unchanged, reset clears imported state |

## Reproduction

```
python scripts/lever.py checks --suite breaker --stage 1 --rev <REV>
```

A failing test that reproduces twice is a REJECT; the protocol line names the class,
the command, its exit code and the output hash.
