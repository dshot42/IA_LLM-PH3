# PLC MES Backend (Flask + TimescaleDB)

## Features
- REST API (JSON)
- `/api/oee` OEE summary (nominal vs real, time-series friendly)
- `/api/machines/live` latest machine states
- WebSocket realtime (Socket.IO)
- SSE streaming PLC events: `/api/plc/stream`
- JWT Auth (login + protected endpoints)
- Pagination for `/api/parts`

## Install
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Run
```bash
python run.py
```

- Health: `GET http://localhost:5000/api/health`
- Login: `POST http://localhost:5000/api/auth/login` JSON `{ "username":"admin","password":"admin123" }`
- Use header: `Authorization: Bearer <token>`

## WebSocket
Socket.IO endpoint: `http://localhost:5000`
Events:
- server emits: `machines_live` (list), `plc_event` (single event)

## Notes / assumptions (OEE)
This backend computes a practical OEE *estimate* using PLC logs:
- `total_cycles` from events with `message ILIKE '%CYCLE_END%'`
- `good_parts` / `bad_parts` from events that look like M5 OK/NOK (message/code/payload)
- `downtime_s` approximated from ERROR events where `duration` is present (otherwise 0)

Adapt the SQL in `app/queries.py` to your exact PLC conventions.
