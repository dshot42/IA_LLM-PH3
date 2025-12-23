import time
import psycopg2
import datetime as dt
from psycopg2.extras import Json

# =========================
# CONFIG DB
# =========================
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "plc"
DB_USER = "postgres"
DB_PASSWORD = "root"

SPEED_FACTOR = 2.0  # UI uniquement (n'influence PAS les timestamps)

# =========================
# TEMPS DE RÉFÉRENCE (FIXE)
# =========================
BASE_TS = dt.datetime(2025, 1, 1, 8, 0, 0, tzinfo=dt.timezone.utc)

# =========================
# DB CONNECTION
# =========================
def conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def sleep_s(seconds: float):
    time.sleep(seconds / max(SPEED_FACTOR, 1e-9))

# =========================
# WORKFLOW NOMINAL
# =========================
WORKFLOW = {
    "machines_order": ["M1", "M2", "M3", "M4", "M5"],
    "scenario_nominal": [
        {"machine": "M1", "start": 0,  "end": 8},
        {"machine": "M2", "start": 8,  "end": 36},
        {"machine": "M3", "start": 36, "end": 54},
        {"machine": "M4", "start": 54, "end": 72},
        {"machine": "M5", "start": 72, "end": 90},
    ],
    "micro_steps": {
        "M1": ["M1.01","M1.02","M1.03","M1.04","M1.05","M1.06","M1.07","M1.08","M1.09","M1.10"],
        "M2": ["M2.01","M2.02","M2.03","M2.04","M2.05","M2.06","M2.07","M2.08","M2.09","M2.10","M2.11","M2.12","M2.13"],
        "M3": ["M3.01","M3.02","M3.03","M3.04","M3.05","M3.06","M3.07","M3.08","M3.09","M3.10","M3.11"],
        "M4": ["M4.01","M4.02","M4.03","M4.04","M4.05","M4.06","M4.07","M4.08","M4.09","M4.10","M4.11"],
        "M5": ["M5.01","M5.02","M5.03","M5.04","M5.05","M5.06","M5.07","M5.08","M5.09","M5.10","M5.11"],
    }
}

# =========================
# SQL
# =========================
INSERT_SQL = """
INSERT INTO plc_events
(ts, part_id, machine, level, code, message, cycle, step_id, step_name, duration, payload)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""

def insert_event(cur, *, ts, part_id, machine, level,
                 code, message, cycle, step_id,
                 step_name, duration, payload=None):
    cur.execute(
        INSERT_SQL,
        (
            ts,
            part_id,
            machine,
            level,
            code,
            message,
            cycle,
            step_id,
            step_name,
            duration,
            Json(payload or {}),
        )
    )
    print(f"insert {ts} {machine} {step_id} {level}")

# =========================
# DB HELPERS
# =========================
def insert_part(cur, part_id: str):
    cur.execute(
        """
        INSERT INTO part (external_part_id, line_id, status)
        VALUES (%s, %s, %s)
        ON CONFLICT (external_part_id) DO NOTHING
        """,
        (part_id, 1, "IN_PROGRESS"),
    )

def clear_db(cur):
    cur.execute("DELETE FROM part")
    cur.execute("DELETE FROM plc_events")
    cur.execute("DELETE FROM plc_anomalies")

# =========================
# SIMULATION NOMINALE
# =========================
def run_nominal_simulator():
    print("=== NOMINAL SIMULATOR (DURATION-INTEGRATED TIME) ===")

    cycle = 1
    part_seq = 1

    with conn() as c:
        c.autocommit = True
        with c.cursor() as cur:

            clear_db(cur)

            while True:
                part_id = f"P{part_seq:06d}"
                part_seq += 1

                # 🔑 TEMPS COURANT = BASE + somme des durations
                current_ts = BASE_TS + dt.timedelta(seconds=(cycle - 1) * 90)

                insert_part(cur, part_id)

                # =================
                # CYCLE START (durée nulle)
                # =================
                insert_event(
                    cur,
                    ts=current_ts,
                    part_id=part_id,
                    machine="SYSTEM",
                    level="INFO",
                    code="CYCLE_START",
                    message="CYCLE_START",
                    cycle=cycle,
                    step_id="S1",
                    step_name="CYCLE",
                    duration=0.0,
                )

                # =================
                # MACHINES
                # =================
                for block in WORKFLOW["scenario_nominal"]:
                    machine = block["machine"]
                    duration_machine = block["end"] - block["start"]

                    steps = WORKFLOW["micro_steps"][machine]
                    step_duration = duration_machine / len(steps)

                    for step_id in steps:
                        # STEP (consomme du temps)
                        insert_event(
                            cur,
                            ts=current_ts,
                            part_id=part_id,
                            machine=machine,
                            level="INFO",
                            code="STEP",
                            message="STEP",
                            cycle=cycle,
                            step_id=step_id,
                            step_name=step_id,
                            duration=step_duration,
                        )

                        # ⏱️ le temps avance UNIQUEMENT ici
                        current_ts += dt.timedelta(seconds=step_duration)
                        sleep_s(step_duration)

                        # STEP_OK (durée nulle)
                        insert_event(
                            cur,
                            ts=current_ts,
                            part_id=part_id,
                            machine=machine,
                            level="OK",
                            code="OK",
                            message="STEP_OK",
                            cycle=cycle,
                            step_id=step_id,
                            step_name=step_id,
                            duration=0.0,
                        )

                # =================
                # CYCLE END (durée nulle)
                # =================
                insert_event(
                    cur,
                    ts=current_ts,
                    part_id=part_id,
                    machine="SYSTEM",
                    level="INFO",
                    code="CYCLE_END",
                    message="CYCLE_END",
                    cycle=cycle,
                    step_id="S6",
                    step_name="CYCLE",
                    duration=0.0,
                )

                cycle += 1


if __name__ == "__main__":
    try:
        run_nominal_simulator()
    except KeyboardInterrupt:
        print("\nStopped.")
