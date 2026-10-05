# Umbra — a software factory that proves its own work

Umbra is seven Band seats, a shared result repository and a few small tools. One human
message per run starts it; from then on the seats plan, build, attack, verify and certify
each stage among themselves, and the lead reports once at the end.

> Measured figures come from `room.json`, `record/`, git history and OpenCode's token
> counts. Nothing here is illustrative output.

## The seats

| Seat | Job | Writes only | Harness / model (submitted run) |
| --- | --- | --- | --- |
| Lead | turns the spec into numbered requirements, rulings and contracts; opens stages; breaks loops | `spec/` | Cursor CLI / composer-2.5 |
| Builder | writes the service, Dockerfile and RUN.md to the spec text; never reads supplied tests | `stage-N/` | Cursor CLI / composer-2.5 |
| Verifier | a check per requirement, a reference model, differential and regression runs, the official checks | `verify/` | Cursor CLI / composer-2.5 |
| Breaker | attacks: concurrency, repetition and ordering, boundaries, resources, durability; binding veto | `attacks/` | OpenCode / deepseek-ai/DeepSeek-V4.1-Flash via Featherless |
| UIReviewer | drives the interface in a real browser at 375 and 1280 px, every named state | `review/` | Cursor CLI / composer-2.5 |
| Certifier | hermetic isolated build, re-executes evidence, runs fault mutants against every suite, seals | `mutants/` | Cursor CLI / composer-2.5 |
| Endurance | recruited by Lead when a stage adds long-lived state: soak, restart, export and import under load | `soak/` | Cursor CLI / composer-2.5 |

Cursor seats use composer-2.5 within the subscription. The attacker is the one metered
seat: DeepSeek-V4.1-Flash through Featherless at $0.30 per million input tokens ($0.03
cached) and $1.20 per million output tokens. The attacker, which holds a veto, is a
different model family from the builder, so the builder's blind spots are not the
attacker's. The other reviewers share the builder's model, so they rely on separation by
evidence instead: each checks against the specification text and its own recorded runs,
never against the builder's account of its work, and every suite must catch the
certifier's fault mutants.

## How bad work is caught

1. **Requirements first.** Lead records every must, limit, error case and example as a
   numbered requirement with its source line. Verifier writes at least one check per
   requirement; `record.py status` shows any requirement with no check or no passing run.
2. **Independent evidence.** Evidence can only be created by `record.py evidence --run`,
   which runs the command itself and stores exit code, output hash and the code revision.
   An ACCEPT is refused unless it cites the reviewer's own passing evidence at the exact
   revision under review.
3. **Mutation gate.** Certifier writes small faults against each invariant and runs them
   through `lever.py mutate` against the official, Verifier and Breaker suites. A fault no
   suite catches means the suites are too weak: Certifier rejects the *reviewers*, not the
   builder, and does not seal until every fault is caught.
4. **Isolated, hermetic certification.** Certifier builds from a clean export of the
   sealed commit and runs the official checks in isolated mode (no outbound network,
   2 CPU, 2 GiB), the same way grading does.

## How it recovers

- A REJECT carries the reproduction command, exit code and output hash; Builder must
  reproduce it before fixing, and resubmits to every reviewer.
- The same check failing three times becomes ESCALATE to Lead, who changes the design or
  the split of work instead of allowing a fourth attempt.
- A REQUEST past its due time gets one reminder, then ESCALATE. A silent seat is named as
  the blocker; no seat does another seat's job.

## The clock: no seat works forever

Agents left alone keep investigating. Umbra bounds every turn from outside the agent:

- `factory/supervise.py` reads Band's turn activity every minute. A turn past its budget
  (30 minutes; 45 for Builder and Certifier, set in `factory/seats.json`) is interrupted
  through Band, and the seat gets a CLOCK message: start nothing new, record and commit
  what has run, send the verdict or SUBMIT. A second overrun asks for ESCALATE to Lead.
- When no seat is working, the room has been quiet for 15 minutes and Lead has not sent
  the final report, the clock wakes Lead to unblock the stage.
- Lead answers an escalation after a CLOCK message with one narrowed REQUEST, then, if
  that also fails, withdraws the unrun checks with a recorded reason
  (`record.py withdraw`). The stage is then judged on the evidence that exists, and any
  requirement left without a check stays unverified and is named in the final report.
- Mandates say the same thing up front: one bounded piece of work per turn, stop at the
  exit condition, report after two failed attempts, give every command a time limit.
- Band posts every turn's closing text as a reply that wakes the seat it answers, so two
  seats that each close with a courtesy note ("Silent turn") wake each other forever. When
  the last six agent messages are such notes traded by two seats within five minutes, the
  supervisor detaches both from the room, so messages for them queue instead of waking
  them. Every minute it drops queued filler and restarts a parked seat only when a message
  with real work is waiting. Restarting both straight away was tried first and the loop
  resumed within a minute. In the first pocketful run this loop formed twice between
  Breaker and Certifier.
- Band's interrupt ends a turn but not the commands the turn started. In the first
  pocketful run Certifier left three copies of a two-hour mutation run going, each
  slowing the others. On an overrun the supervisor now also kills every process under
  the seat's agent process (found by the seat's launcher on its command line).
- A runtime can hang while still accepting messages: in the first pocketful run Breaker
  took four SUBMITs over two hours and never started a turn, and the stage stalled behind
  its missing verdict while the turn clock, which only times turns that start, saw
  nothing. The supervisor now treats a seat that was sent real work over ten minutes ago
  and has neither replied nor started a turn since as hung. It detaches the seat, kills
  its agent process (restarting the room session reuses the hung process), queues a CLOCK
  saying which messages were lost, and starts a fresh worker. A Cursor worker can take
  over a minute to start on a loaded machine, so restarts get five minutes.
- Reviving Lead failed every ten minutes for two hours: Band refuses a plain restart while
  a seat still holds a session in any room, and Lead holds one in every room it created.
  Each attempt killed Lead's worker and sent another CLOCK, which read as Certifier
  looping. Revive now detaches every session the seat holds, sends the CLOCK once per
  incident, and gives up after two replacements. It also skips the check when Band does
  not answer the activity query, since an empty answer made every seat look hung.
- The first pocketful dispatch carried only the stage 1 specification and told Lead to
  open later stages itself. Lead fetched stage 2 with a helper it wrote, then reported
  "no stage 3 in spec/repo" and closed the run after stage 2. A dispatch now carries every
  stage it asks for, verbatim, and the handoff tool cuts each stage's text at the next
  stage's heading; when the stages do not fit in one message, the dispatch asks for fewer.
- Nine Builder commits in pocketful stage 2 (22:37 to 00:27, including the sealed
  `b013f5e`) went through plain `git commit` and carry the machine owner's name with a
  `Co-authored-by: Cursor` trailer; their messages cite Builder's evidence ids
  (`E-builder-7..9`) and Builder's SUBMITs name those revisions. Seeded
  repositories now get a pre-commit hook that refuses any commit not made through
  `scripts/commit.py`, which commits as the seat.
- Unparking Lead after a filler loop hit the same refused restart and left Lead detached
  for over an hour with stage 3 work queued. Every supervisor restart of a seat now detaches
  all its room sessions first, and a supervisor that starts up treats any seat already
  detached from the room as parked, so queued work still reaches it. A plain restart can
  report "Connected" and leave the room session detached (Breaker sat dormant that way
  while the room still showed its interrupted turn as "Reasoning"), so the supervisor
  checks the session's binding after each restart and restarts the room session if needed.
- A turn can end on a transient model error ("RetriableError: http/2 stream closed")
  halfway through a task, and nothing wakes the seat again. When a seat's newest message is
  such an error and it has done nothing since, the supervisor sends it one CLOCK to resume.
- Band caps a room at 30,000 messages, counting tool calls and thoughts. The pocketful
  room reached it during stage 4 after about 40 hours, and from then on every post failed
  ("max_messages_per_room_count"). Stage 4 continued in a new room with the same seats and
  repository; the record carries every requirement and verdict across, so no context
  depends on the old room. Its last turn indicators stay frozen, since the room cannot
  accept the turn-ended event.
- Stopping a command tree with `taskkill /F` skips the cleanup of PyInstaller-packed tools,
  which leave a 1.2 GB `_MEI*` folder in `%LOCALAPPDATA%\Temp` each time; twenty of them
  filled the disk and a seat failed with "database or disk is full". Delete the unlocked
  ones after a long run.
- Filler loops run at about seven messages a minute, and a full supervisor cycle on a
  loaded machine can take several minutes, so a loop could post dozens of messages toward
  the room cap before it was seen. The supervisor now checks only for loops every 15 s
  between cycles, and parks the pair after four filler replies instead of six. A seat with
  nothing left to do can also answer every acknowledgment from several seats at once, which
  no pair test sees; four filler replies from one seat within three minutes now park that
  seat too, unless it has a turn running.
- A scheduled task ("Umbra supervisor standby", every five minutes) starts the supervisor
  again if it is not running for the room, so the clock survives editor restarts.
- Run the supervisor detached from any editor or terminal (`Start-Process ... -WindowStyle
  Hidden`); closing the window that started it stopped the clock for an hour.
- CLOCK messages are marked automatic and go out through Lead's session (Certifier's when
  waking Lead). The clock never writes as the human.

## What the tools enforce, not just ask

- **Identity.** `commit.py`, `record.py`, `handoff.py` and `report.py` read the calling
  seat from the process tree (the seat's launcher appears among its ancestors), so a seat
  cannot act under another seat's name, even from a helper process it starts.
  Development runs showed why: an early lead, unable to hand off, built the service itself
  and committed it as the builder.
- **Ownership.** `commit.py` commits only the seat's own paths, under its own name. Check
  identifiers belong to the seat that registered them.
- **The seal.** `record.py verdict --kind SEAL` is refused unless every requirement of the
  stage is verified at that revision: each reviewer check covering it has a clean, passing
  run by its owner at that exact revision. Only Certifier can seal.
- **Complete handoffs.** `handoff.py` sends a REQUEST carrying the stage specification
  exactly as the human dispatched it, the requirement ids and every contract, split into
  parts when long. A seat never works from a summary.
- **One final report.** `report.py` addresses the report to the human who dispatched the
  run; nothing else reaches the human.
- **Genericity.** `factory/lint_mandates.py` runs the organisers' vocabulary scan for every
  track plus a domain-word denylist; mandates were written and linted before the track
  specification was read.

## Reusing it

```
python factory/seed.py --repo <empty folder> --track <track> --profile run
python factory/create_seats.py --profile run --repo <repo> --create
python factory/reset_seats.py            # seats out of old rooms, queues cleared, parked
band --session umbra-lead chat new --with <owner>/<seat> ... --with <owner>
python factory/supervise.py --room <room>  # restarts a runtime that fails its handshake
python factory/dispatch.py --track <track> --stage 1 --last-stage 4 --repo <repo> --send <room>
```

`supervise.py` never posts or reads the conversation: it only restarts a seat's runtime
when Band reports a failed handshake, which delivers that seat's queued messages.

`factory/seats.json` holds the roster, owned paths and model profiles; `mandates/src/` the
seat mandates. Nothing in either names a track.

## Cost and time

Wall time runs from Lead's requirements commit to Certifier's SEAL commit; rejections are
REJECT verdicts in `record/`.

| Stage | Sealed rev | Wall time | Rejections | Mutation score |
| --- | --- | --- | --- | --- |
| 1 | `1125eee49810` | 5 h 50 min | 5 | 3/3 |
| 2 | `b013f5e17143` | 12 h 04 min, roughly 4.5 h of it hung runtimes (Breaker, then Lead) | 6 | 3/3 |
| 3 | `55207f5fd143` | 12 h 00 min | 3 | 3/3 |
| 4 | `79af98560dd9` | 12 h 31 min (requirements 22:04 to SEAL 10:35 next day) | 6 | not scored: mutants m01-m03 were withdrawn before they ran |

Spend: the five Cursor seats in the run (Endurance was never recruited) ran on composer-2.5 inside the Cursor subscription, with no
per-token charge. Breaker, the one metered seat, used 1,397 model calls on
DeepSeek-V4.1-Flash over the whole run: 19.3 M input tokens, 83.5 M cached input tokens
and 0.86 M output tokens, about $9.32 at Featherless list prices (OpenCode's own token
counts; Band's usage view does not see either harness).

Stage 4 seal: official checks run in isolation passed (exit 0) and the record shows
28/28 requirements verified at `79af98560dd9`. The clock expired before Certifier's
re-execution (S4-CC2) and mutation checks (S4-CC3, m01-m03) could run, so Lead withdrew
them under ruling S4-U13 (`record.py withdraw`); stage 4 was sealed on the evidence that
exists. This is the one stage where the mutation gate in "How bad work is caught" was not
completed.

## What it costs to work this way

- Seven seats on one machine compete for CPU and memory; a Cursor seat must start within
  Band's 30 s handshake, so seats launch Cursor's runtime directly instead of through its
  shell shim.
- Each Cursor session used to start its own copies of every MCP server in the operator's
  editor configuration and leave them running; on the development machine that leaked
  about a hundred processes and exhausted memory mid-run. Each seat now gets its own home
  folder for the Cursor runtime with an empty server list, and OpenCode seats get an
  isolated configuration that enables only their one provider.
- Band revives a seat in every room it still belongs to and delivers that room's queued
  messages. In one rehearsal, seats from the previous night's room woke on its stale
  requests and worked on the new repository. `reset_seats.py` now removes seats from old
  rooms and clears their queues before every run. When a removal silently failed, a
  previous room ran a second, duplicate stage-1 run beside the rehearsal for a whole
  morning, so the reset now checks membership afterwards and refuses to report ready
  while any seat is still in an old room.
- `lever.py stop` used to remove every seat's services, which killed Breaker's suites
  mid-run. Each service now records the seat that booted it, and `stop` removes only the
  caller's own unless given `--all`.
- Every final text of a turn is posted as a reply that wakes the seat it answers, so a
  courtesy reply restarts a conversation. Mandates require ending a turn with no text
  when nothing is needed.
- Mutation runs rebuild the service per fault, which dominates certification time.
- Pasting the full specification into every handoff costs tokens; the alternative, a file
  pointer, was observed to let seats work from a summary.
