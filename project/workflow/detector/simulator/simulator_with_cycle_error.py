import time
import random
import uuid
import datetime as dt
import psycopg2
from psycopg2.extras import Json

SPEED_FACTOR = 4      # 1.0 = temps réel
JITTER_RATIO = 0.05
ANOMALY_PROBABILITY = 0.5
DEPHASING_MULTIPLIER = 5


# ============================================================
# DB
# ============================================================
def conn():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="plc",
        user="postgres",
        password="root"
    )

INSERT_SQL = """
INSERT INTO plc_events (
    ts, part_id, machine, level, code, message,
    cycle, step_id, step_name, duration, payload
)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""

def insert_event(cur, **e):
    cur.execute(INSERT_SQL, (
        e["ts"], e["part_id"], e["machine"], e["level"],
        e["code"], e["message"], e["cycle"],
        e["step_id"], e["step_name"],
        e["duration"], Json(e.get("payload"))
    ))

# ============================================================
# WORKFLOW (extrait utile)
# ============================================================
SCENARIO = [
    {"machine": "M1", "step": "S1", "start": 0,  "end": 8},
    {"machine": "M2", "step": "S2", "start": 8,  "end": 36},
    {"machine": "M3", "step": "S3", "start": 36, "end": 54},
    {"machine": "M4", "step": "S4", "start": 54, "end": 72},
    {"machine": "M5", "step": "S5", "start": 72, "end": 90},
]

WORKFLOW_STEPS = {
    "M1": [s["id"] for s in [
        {"id": "M1.01"}, {"id": "M1.02"}, {"id": "M1.03"}, {"id": "M1.04"},
        {"id": "M1.05"}, {"id": "M1.06"}, {"id": "M1.07"}, {"id": "M1.08"},
        {"id": "M1.09"}, {"id": "M1.10"},
    ]],
    "M2": [s["id"] for s in [
        {"id": "M2.01"}, {"id": "M2.02"}, {"id": "M2.03"}, {"id": "M2.04"},
        {"id": "M2.05"}, {"id": "M2.06"}, {"id": "M2.07"}, {"id": "M2.08"},
        {"id": "M2.09"}, {"id": "M2.10"}, {"id": "M2.11"}, {"id": "M2.12"},
        {"id": "M2.13"},
    ]],
    "M3": [s["id"] for s in [
        {"id": "M3.01"}, {"id": "M3.02"}, {"id": "M3.03"}, {"id": "M3.04"},
        {"id": "M3.05"}, {"id": "M3.06"}, {"id": "M3.07"}, {"id": "M3.08"},
        {"id": "M3.09"}, {"id": "M3.10"}, {"id": "M3.11"},
    ]],
    "M4": [s["id"] for s in [
        {"id": "M4.01"}, {"id": "M4.02"}, {"id": "M4.03"}, {"id": "M4.04"},
        {"id": "M4.05"}, {"id": "M4.06"}, {"id": "M4.07"}, {"id": "M4.08"},
        {"id": "M4.09"}, {"id": "M4.10"}, {"id": "M4.11"},
    ]],
    "M5": [s["id"] for s in [
        {"id": "M5.01"}, {"id": "M5.02"}, {"id": "M5.03"}, {"id": "M5.04"},
        {"id": "M5.05"}, {"id": "M5.06"}, {"id": "M5.07"}, {"id": "M5.08"},
        {"id": "M5.09"}, {"id": "M5.10"}, {"id": "M5.11"},
    ]],
}

def clear_db(c,cur):
    cur.execute(
        "DELETE FROM part"
    )
    c.commit()
    cur.execute(
    "DELETE FROM plc_events"
    )
    c.commit()
    cur.execute(
    "DELETE FROM plc_anomalies"
    )
    c.commit()

def insert_part(c,cur, part_id: str):
    cur.execute(
        """
        INSERT INTO part (external_part_id, line_id, status)
        VALUES (%s, %s, %s)
        ON CONFLICT (external_part_id) DO NOTHING
        """,
        (part_id, 1, "IN_PROGRESS"),
    )
    c.commit()
    print("part inserted id = ", part_id)
    
# ============================================================
# SIMULATION
# ============================================================

ANOMALY_TYPES = ["NONE", "TIME_DEPHASING", "PLC_ERROR", "SEQUENCE_VIOLATION"]


def run_simulator():
    cycle = 1

    with conn() as c, c.cursor() as cur:
        clear_db(c,cur)
        while True:
            part_id = f"P-{uuid.uuid4().hex[:8]}"
            insert_part(c,cur,part_id)
            base_ts = dt.datetime.now(dt.timezone.utc)

            anomaly = random.choice(ANOMALY_TYPES) if random.random() < ANOMALY_PROBABILITY else "NONE"

            print(f"▶ Cycle {cycle} | part={part_id} | anomaly={anomaly}")

            current_ts = base_ts
            last_machine = None

            for i, s in enumerate(SCENARIO):
                machine = s["machine"]

                # 🔀 violation de séquence : sauter M4 parfois
                if anomaly == "SEQUENCE_VIOLATION" and machine == "M4":
                    print("⚠️ SEQUENCE VIOLATION: skipping M4")
                    continue

                machine_duration = (s["end"] - s["start"])
                steps = WORKFLOW_STEPS[machine]
                step_nominal = machine_duration / len(steps)

                for step_id in steps:
                    dur = step_nominal * (1 + random.uniform(-JITTER_RATIO, JITTER_RATIO))

                    # ⏱️ Déphasage sporadique (sur un step précis)
                    if anomaly == "TIME_DEPHASING" and machine == "M2" and step_id == "M2.07":
                        dur *= DEPHASING_MULTIPLIER
                        print("⏱️ DEPHASING on", step_id)

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
                        duration=dur,
                        payload={"anomaly": anomaly},
                    )

                    # ❌ PLC ERROR sporadique
                    if anomaly == "PLC_ERROR" and machine == "M3" and step_id == "M3.06":
                        insert_event(
                            cur,
                            ts=current_ts,
                            part_id=part_id,
                            machine=machine,
                            level="ERROR",
                            code="E-M3-021",
                            message="ROUGHNESS_NOK",
                            cycle=cycle,
                            step_id=step_id,
                            step_name=step_id,
                            duration=0,
                            payload={"error": True},
                        )
                        print("❌ PLC ERROR on", step_id)

                    time.sleep(dur / SPEED_FACTOR)
                    current_ts += dt.timedelta(seconds=dur)


if __name__ == "__main__":
    try:
        run_simulator()
    except KeyboardInterrupt:
        print("Stopped.")
