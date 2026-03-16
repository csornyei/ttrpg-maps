# Daggerheart backend

## Storage

- POIs are now persisted in a SQLite database at `src/data/pois.db`.
- On first startup, if the database is empty, seed data is loaded from `src/data/pois.json`.
- Moving POIs keep their movement path and current path index in the database.

## API

- `GET /api/pois` - list all POI summaries
- `GET /api/pois/{poi_id}` - get one POI detail
- `POST /api/pois` - create a POI
- `PUT /api/pois/{poi_id}` - replace/update a POI
- `DELETE /api/pois/{poi_id}` - delete a POI

## Configuration

Set these environment variables before starting the backend:

- `ENV` - `dev` or `prod` (default: `dev`)
- `API_AUTH_TOKEN` - shared secret for write endpoints (required)
- `FRONTEND_ORIGIN` - required when `ENV=prod`, for example `https://map.example.com`
- `LOG_LEVEL` - logging verbosity (default: `INFO`)

### CORS behavior

- `ENV=dev`: allows all CORS origins.
- `ENV=prod`: allows only `FRONTEND_ORIGIN`.

### Write endpoint authentication

These endpoints require authentication:

- `POST /api/pois`
- `PUT /api/pois/{poi_id}`
- `DELETE /api/pois/{poi_id}`

Send either:

- `Authorization: Bearer <API_AUTH_TOKEN>`
- `X-API-Key: <API_AUTH_TOKEN>`

## Health and metrics

- `GET /health/live` - liveness probe
- `GET /health/ready` - readiness probe (checks storage connectivity)
- `GET /metrics` - Prometheus metrics

Exported metrics include:

- frontend loads (`daggerheart_frontend_loads_total`)
- active websocket connections (`daggerheart_ws_active_connections`)
- websocket messages (`daggerheart_ws_messages_total`)
- HTTP response counts by method/path/status (`daggerheart_http_responses_total`)

### Create/Update payload shape

Provide exactly one position mode:

- Static POI: include `col` and `row`
- Moving POI: include `path` (non-empty list of `{ "col": int, "row": int }`)

Example static payload:

```json
{
  "id": "new-hamlet",
  "name": "New Hamlet",
  "color": "#5b7cfa",
  "description": "A newly founded settlement.",
  "notes": "Under construction.",
  "col": 12,
  "row": 7
}
```

Example moving payload:

```json
{
  "id": "patrol-1",
  "name": "Patrol 1",
  "color": "#c0392b",
  "description": "A mobile patrol.",
  "notes": "Loops through a fixed route.",
  "path": [
    { "col": 10, "row": 10 },
    { "col": 11, "row": 10 },
    { "col": 11, "row": 11 }
  ]
}
```
