# pmus-kalshi-mapper

Maps Polymarket US pregame sports instruments to their Kalshi markets. Every answer is either resolved
(a ticker, a side and the rung that proved it) or refused with a reason. Aliases the rungs cannot settle
are decided by the review model and stored; rows added by hand are optional overrides.

## Setup

```
python -m venv venv && venv/bin/pip install -r requirements.txt
cp keys/keys.example.json keys/keys.json      # PMUS, Kalshi and Anthropic credentials; gitignored
export DATABASE_URL=postgresql+psycopg://mapper:mapper@localhost:5432/mapper
PYTHONPATH=. venv/bin/python -m mapper init-db
```

## Use

The API is the interface (see Service). `POST /resolve` takes PMUS symbols, resolves them live against
PMUS and Kalshi, records a run and returns `{run, results}`; the page in `web/` calls the same routes.

## Tables

`instruments` (PMUS rows as the engine reads them), `event_mappings` (successful event joins),
`outcomes` (one row per symbol per run: ticker, side, rung, reason, the populated PMUS fields), `team_aliases`,
`player_aliases`, `overrides` (the manual tables), `review_log` (every question put to the model).

## Service

`api/app.py` (Flask) serves the same operations over HTTP and the page in `web/` (React, esbuild):
`POST /resolve {"symbols": [...]}` → `{run, results}`, `GET /drift`, `GET|PUT|DELETE /overrides`,
`GET|PUT|DELETE /aliases/{teams,players}` (`?source=review,manual` filters teams). Locally:
`gunicorn api.app:app` after `(cd web && npm run build)`. `bash scripts/deploy.sh` builds the image and
restarts it on the box (`terraform/` holds the one EC2 and the RDS Postgres it talks to).
