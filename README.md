# Pocketful — band result repository

Track: **pocketful**. Stages live under `stage-N/`. Lead owns `spec/` and `record/`; Builder owns `stage-*/`.
How the run was produced and measured: see [FACTORY.md](FACTORY.md).

Stage 1: payments, requests, splits, activity feed, settlements, auth, reset/export/import test hooks.
Stage 2: sealed **b013f5e17143** — UI, authorizations, captures.
Stage 3: sealed **55207f5fd143** — statements, payment corrections, temporal reads, snapshot pagination.
Stage 4: sealed **79af98560dd9** — refunds and correction batches (28/28; mutation checks withdrawn, see FACTORY.md).

## Live demo

Stage 4 is deployed at <https://pocketful-stage4.onrender.com> (sealed revision 79af98560dd9 plus the final UI). The free host sleeps when idle, so the first request can take about a minute. Demo accounts: `ada@example.com`, `bob@example.com`, `cy@example.com`, password `correct horse`. Data resets whenever the host restarts.

## Build and open stage 4

Requires Docker.

```sh
cd stage-4
docker build -t pocketful-stage4 .
docker run --rm -e PORT=8080 -p 8080:8080 pocketful-stage4
```

Open <http://localhost:8080/> (sign up at `/signup`, log in at `/login`). Health check: `GET /health`.
Other pages: `/requests`, `/authorizations`, `/split`.
