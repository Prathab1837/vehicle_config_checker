# Vehicle Config Checker

FastAPI + LangGraph (plain Python nodes, no LLM) + PostgreSQL (SQLAlchemy 2.0 async) + Redis.

## Run (3 commands)
```bash
cp .env.example .env
docker compose up --build -d
open http://localhost:8000/docs        # Swagger UI
```
Run tests (no DB/Redis needed): `pip install -r requirements.txt && pytest`

## Reproduce the worked example
```bash
curl -s -X POST localhost:8000/configs -H 'Content-Type: application/json' \
  -d '{"vehicle_type":"3w_cargo","length":3000,"width":1600,"height":2050,"wheelbase":2200,"payload":500}'
```
Response:
```json
{"id":1,"vehicle_type":"3w_cargo",
 "input":{"length":3000,"width":1600,"height":2050,"wheelbase":2200,"payload":500},
 "output":{"length":3000,"width":1500,"height":1950,"wheelbase":2200,"payload":500},
 "adjustments":[
  {"iteration":1,"field":"width","rule":"range","from":1600,"to":1500},
  {"iteration":2,"field":"height","rule":"R2","from":2050,"to":1950}],
 "status":"adjusted","iterations":3}
```

## Design notes
- `iterations` = number of validate passes (the final clean pass counts, so the example gives 3).
- Status: `valid` (no fixes), `adjusted` (fixed and clean), `rejected` (a fix leaves its own limits, or still broken after 3 passes).
- Pure logic lives in `app/rules.py`; graph wiring in `app/graph.py`; Redis/DB access in `app/service.py`.
- Graph is compiled once at startup. Limits cached at `limits:{vehicle_type}`, TTL 10 min; `PUT /limits/...` deletes the key.
- Tables are created and seeded on startup (`create_all`).

## Finished
All 5 endpoints, graph loop, Redis cache + invalidation, 422/404 handling, pytest for the graph, Docker Compose.

## Skipped
Alembic migrations (startup `create_all` used instead to keep it simple); API-level integration tests.
