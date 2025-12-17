from sqlalchemy import text
import time
from datetime import datetime, timedelta, timezone
from threading import Thread
from datetime import datetime
from decimal import Decimal
from flask_socketio import SocketIO
import pandas as pd

# imports internes au package supervision_handler.app
from supervision_handler.app.extensions import socketio
from supervision_handler.app.models import PlcEvent
from supervision_handler.app.connect import get_conn
from supervision_handler.app import queries
from supervision_handler.app.config import LIVE_POLL_MS
from supervision_handler.app.service import part_service
from supervision_handler.app.factory import db
# import cross-package (OK)
from workflow.detector.launch_detection import check_anomalies
from workflow.detector.feature_handler import fetch_last_event


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

def init_socketio(socketio: SocketIO, app):
    global _started
    if _started:
        return
    _started = True
    def poll_loop():
        with app.app_context():   # 🔴 CONTEXTE UNIQUE POUR LE THREAD
            last_ts_by_machine = {}

            while True:
                try:
                    # --- QUERY LIVE MACHINES ---
                    rows = (
                        db.session
                        .execute(text(queries.MACHINES_LIVE))
                        .mappings()
                        .all()
                    )

                    rows = [dict(r) for r in rows]
                    socketio.emit("machines_live", json_safe(rows))

                    for r in rows:
                        m = r.get("machine")
                        ts = r.get("last_ts")
                        if not ts or not m:
                            continue

                        prev = last_ts_by_machine.get(m)
                        if prev is None or ts > prev:
                            update_part(ts)

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

                            print("push socket event", ts)

                            check_anomalie_on_detector()

                except Exception:
                    import traceback
                    traceback.print_exc()

                time.sleep(max(LIVE_POLL_MS, 100) / 1000.0)

    Thread(target=poll_loop, daemon=True).start()
    
    

def update_part(ts):
    last_event:PlcEvent = (
        PlcEvent.query
        .filter(
            PlcEvent.ts == ts
        )
        .first()
    )

    if last_event:
        part_service.update_part_from_event(last_event)
                        
def check_anomalie_on_detector():
    param = {
        "only_last": False,
        "start":  datetime.now(timezone.utc) - timedelta(days=2),
        "end": datetime.now(timezone.utc),
        "part_id": "",
        "ligne": "",
        "LLM_RESULT" : False
    }
    event_df = fetch_last_event()
    check_anomalies(event_df,param)        
    
                 
                    