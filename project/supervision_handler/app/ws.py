import time
from threading import Thread
from flask_socketio import SocketIO
from .connect import get_conn
from . import queries
from .config import LIVE_POLL_MS

_started = False

def init_socketio(socketio: SocketIO):
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

                socketio.emit("machines_live", rows)

                for r in rows:
                    m = r.get("machine")
                    ts = r.get("last_ts")
                    if not ts or not m:
                        continue
                    prev = last_ts_by_machine.get(m)
                    if prev is None or ts > prev:
                        last_ts_by_machine[m] = ts
                        socketio.emit("plc_event", {
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
                        })
            except Exception:
                pass

            time.sleep(max(LIVE_POLL_MS, 100) / 1000.0)

    Thread(target=poll_loop, daemon=True).start()
