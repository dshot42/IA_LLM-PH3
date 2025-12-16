import time
from threading import Thread
from flask_socketio import SocketIO

from .models import PlcEvent
from .connect import get_conn
from . import queries
from .config import LIVE_POLL_MS
from app.extensions import socketio
from datetime import datetime
from decimal import Decimal
from app.service import part_service
from . import queries


_started = False

def json_safe(obj):
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_safe(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def init_socketio(socketio: SocketIO,app):
    global _started
    if _started:
        return
    _started = True

    def poll_loop():
        last_ts_by_machine = {}
        while True:
            try:
                with get_conn() as conn, conn.cursor() as cur:
                    cur.execute(queries.MACHINES_LIVE)
                    rows = cur.fetchall()

                socketio.emit("machines_live", json_safe(rows))

                for r in rows:
                    m = r.get("machine")
                    ts = r.get("last_ts")
                    if not ts or not m:
                        continue
                    
                    prev = last_ts_by_machine.get(m)
                    if prev is None or ts > prev:
                        update_part(ts, app)
                        last_ts_by_machine[m] = ts
                        socketio.emit("plc_event", json_safe({
                            "ts": ts.isoformat(),
                            "part_id": r.get("last_part_id"),
                            "machine": m,
                            "level": r.get("last_level"),
                            "code": r.get("last_code"),
                            "message": r.get("last_message"),
                            "cycle": r.get("last_cycle"),
                            "step_id": r.get("last_step_id"),
                            "step_name": r.get("last_step_name"),
                            "duration": float(r["last_duration"]) if r.get("last_duration") is not None else None,
                            "payload": r.get("last_payload"),
                        }))
                                                         
                        print("push socket ")

            except Exception as e:
                print("❌ Erreur poll_loop:", e)

            time.sleep(max(LIVE_POLL_MS, 100) / 1000.0)

    Thread(target=poll_loop, daemon=True).start()

def update_part(ts,app):
    with app.app_context():
        last_event:PlcEvent = (
            PlcEvent.query
            .filter(
                PlcEvent.ts == ts
            )
            .first()
        )

        if last_event:
            part_service.update_part_from_event(last_event)
                        
                        
                        
@socketio.on("connect")
def on_connect():
    print("🟢 CLIENT CONNECTÉ AU BACKEND")
    socketio.emit("plc_event", {
        "msg": "HELLO FROM BACKEND"
    })