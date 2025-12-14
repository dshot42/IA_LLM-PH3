import os
import json
import time
import random
import datetime as dt
from dataclasses import dataclass
from typing import List, Dict, Optional

import psycopg2
from psycopg2.extras import Json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import launch_detection

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "plc")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

# Real-time behavior
SPEED_FACTOR = float(os.getenv("SIM_SPEED", "1.0"))  # 1.0 = real time, 2.0 = 2x faster
JITTER_RATIO = float(os.getenv("SIM_JITTER", "0.10"))  # +/- 10% random jitter on step durations

# Anomaly injection
ANOMALY_EVERY_N_CYCLES = int(os.getenv("SIM_ANOM_EVERY", "7"))  # anomaly every 7 cycles
ANOMALY_TYPE = os.getenv("SIM_ANOM_TYPE", "M2_SLOWDOWN")        # M2_SLOWDOWN | M5_NOK | DEPHASING
ANOMALY_MULTIPLIER = float(os.getenv("SIM_ANOM_MULT", "1.8"))   # slowdown factor


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def sleep_s(seconds: float):
    # speed factor: if SPEED_FACTOR=2 -> wait half the time
    time.sleep(max(seconds / max(SPEED_FACTOR, 1e-9), 0.0))


def conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )


# ------------------------------------------------------------
# WORKFLOW (based on your JSON)
# ------------------------------------------------------------
WORKFLOW = {
    "line_name": "Ligne 5 machines - Usinage complet",
    "cycle_nominal_s": 90,
    "machines_order": ["M1", "M2", "M3", "M4", "M5"],
    "machines_nominal_s": {"M1": 8, "M2": 28, "M3": 18, "M4": 18, "M5": 12},
    "micro_steps": {
        "M1": [
            ("M1.01", "WAIT_ENTRY"), ("M1.02", "CONVEY_IN"), ("M1.03", "DETECT_PIECE"),
            ("M1.04", "SLOW_ALIGN"), ("M1.05", "SIDE_ALIGNMENT"), ("M1.06", "CLAMP_CLOSE"),
            ("M1.07", "CLAMP_VERIFY"), ("M1.08", "ID_READ"), ("M1.09", "POSITION_CHECK"),
            ("M1.10", "READY_SIGNAL"),
        ],
        "M2": [
            ("M2.01", "WAIT_M1_READY"), ("M2.02", "FIXTURE_LOCK"), ("M2.03", "TOOL_CHECK"),
            ("M2.04", "SPINDLE_RAMP_UP"), ("M2.05", "COOLANT_ON"), ("M2.06", "APPROACH_POS"),
            ("M2.07", "ROUGH_PASS_1"), ("M2.08", "ROUGH_PASS_2"), ("M2.09", "TOOLWEAR_CHECK"),
            ("M2.10", "RETURN_SAFE_POS"), ("M2.11", "SPINDLE_STOP"), ("M2.12", "CHIP_CLEAN"),
            ("M2.13", "DONE_SIGNAL"),
        ],
        "M3": [
            ("M3.01", "WAIT_M2_DONE"), ("M3.02", "FINE_FIXTURE_CHECK"), ("M3.03", "TOOL_VERIFY_FINISH"),
            ("M3.04", "SPINDLE_FINE_RAMP"), ("M3.05", "APPROACH_FINISH"), ("M3.06", "FINISH_PASS_1"),
            ("M3.07", "FINISH_PASS_2"), ("M3.08", "SURFACE_SENSOR_CHECK"), ("M3.09", "OPTIONAL_PROBE"),
            ("M3.10", "CLEAN_AIR"), ("M3.11", "DONE_SIGNAL"),
        ],
        "M4": [
            ("M4.01", "WAIT_M3_DONE"), ("M4.02", "TOOL_SELECT_DRILL"), ("M4.03", "DRILL_APPROACH"),
            ("M4.04", "DRILL_EXEC"), ("M4.05", "DRILL_RETRACT"), ("M4.06", "TOOL_SELECT_TAP"),
            ("M4.07", "TAP_ENGAGE"), ("M4.08", "TAP_MONITOR_TORQUE"), ("M4.09", "TAP_RETRACT"),
            ("M4.10", "HOLE_CLEAN"), ("M4.11", "DONE_SIGNAL"),
        ],
        "M5": [
            ("M5.01", "WAIT_M4_DONE"), ("M5.02", "RECEIVE_PART"), ("M5.03", "VISION_TRIGGER"),
            ("M5.04", "ACQ_2D"), ("M5.05", "ACQ_3D"), ("M5.06", "FEATURE_MEASURE"),
            ("M5.07", "COMPARE_SPECS"), ("M5.08", "LIGHT_DEBURR"), ("M5.09", "UNCLAMP"),
            ("M5.10", "UNLOAD_TO_BIN"), ("M5.11", "LOG_RESULT"),
        ],
    },
    # We use these markers to make /api/oee work out-of-the-box:
    "cycle_end_message": "CYCLE_END",
    "m5_ok_message": "M5_OK",
    "m5_nok_message": "M5_NOK",
}

# Distribute machine nominal time across micro-steps (simple weights)
DEFAULT_STEP_WEIGHTS = {
    "WAIT": 0.05, "CHECK": 0.06, "LOCK": 0.05, "RAMP": 0.06, "ON": 0.03,
    "APPROACH": 0.05, "PASS": 0.18, "EXEC": 0.18, "RETRACT": 0.06,
    "CLEAN": 0.05, "SIGNAL": 0.03, "MEASURE": 0.12, "COMPARE": 0.10,
    "ACQ": 0.08, "TRIGGER": 0.04, "UNLOAD": 0.08, "UNCLAMP": 0.05,
    "ALIGN": 0.07, "CLAMP": 0.06, "READ": 0.05, "DETECT": 0.05,
    "TOOL": 0.05, "CHIP": 0.05, "PROBE": 0.06, "TORQUE": 0.06,
    "DEBURR": 0.05, "FEATURE": 0.10,
}


def micro_step_weight(step_name: str) -> float:
    u = step_name.upper()
    for k, w in DEFAULT_STEP_WEIGHTS.items():
        if k in u:
            return w
    return 0.06


def split_nominal(machine: str) -> List[float]:
    steps = WORKFLOW["micro_steps"][machine]
    weights = [micro_step_weight(name) for _, name in steps]
    s = sum(weights) or 1.0
    nominal = WORKFLOW["machines_nominal_s"][machine]
    return [nominal * (w / s) for w in weights]


# ------------------------------------------------------------
# INSERT HELPERS
# ------------------------------------------------------------
INSERT_SQL = """
INSERT INTO plc_events (ts, part_id, machine, level, code, message, cycle, step_id, step_name, duration, payload)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def insert_event(c, cur, *, ts, part_id, machine, level, code, message, cycle, step_id, step_name, duration, payload):
    cur.execute(
        INSERT_SQL,
        (ts, part_id, machine, level, code, message, cycle, step_id, step_name, duration, Json(payload) if payload is not None else None)
    )
    c.commit()   # 👈 OBLIGATOIRE ICI
    print("ok insert ",  (ts, part_id, machine, level, code, message, cycle, step_id, step_name, duration, Json(payload) if payload is not None else None))
    # call detector to show if any anormalie 
    param = {
        "only_last": True,
    }
    launch_detection.check_anomalies(param)

def insert_part(c,cur, part_id: str):
    INSERT_PART_SQL = """
        INSERT INTO part (external_part_id, line_id, status)
        VALUES (%s, %s, %s)
        ON CONFLICT (external_part_id) DO NOTHING
        RETURNING id
    """

    cur.execute(INSERT_PART_SQL, (part_id, 1, "IN_PROGRESS"))
    c.commit()   # 👈 OBLIGATOIRE ICI
    print("Insert part : ",(part_id, 1, "IN_PROGRESS"))
  
def clear_db(c,cur):
    cur.execute(
        "DELETE FROM part"
    )
    c.commit()
    cur.execute(
    "DELETE FROM plc_events"
    )
    c.commit()
# ------------------------------------------------------------
# SIMULATION
# ------------------------------------------------------------
def run_sim():
    print("=== Production simulator started ===")
    print(f"DB: {DB_HOST}:{DB_PORT}/{DB_NAME} user={DB_USER}")
    print(f"SPEED_FACTOR={SPEED_FACTOR} JITTER={JITTER_RATIO*100:.0f}%")
    print(f"ANOMALY_EVERY={ANOMALY_EVERY_N_CYCLES} TYPE={ANOMALY_TYPE} MULT={ANOMALY_MULTIPLIER}")

    cycle = 1
    part_seq = 1

    with conn() as c:
        c.autocommit = True
        with c.cursor() as cur:
            clear_db(c,cur)
            
            while True:
                
                part_id = f"P{utcnow().strftime('%Y%m%d')}-{part_seq:06d}"
                part_seq += 1
                insert_part(c,cur,part_id)
                

                is_anomaly = (cycle % ANOMALY_EVERY_N_CYCLES == 0)
                anomaly_meta = {"enabled": is_anomaly, "type": ANOMALY_TYPE, "cycle": cycle}

                # Start marker (optional)
                insert_event(c,
                    cur,
                    ts=utcnow(),
                    part_id=part_id,
                    machine="SYSTEM",
                    level="INFO",
                    code="SIM",
                    message="CYCLE_START",
                    cycle=cycle,
                    step_id="S1",
                    step_name="CYCLE",
                    duration=None,
                    payload={"sim": True, "part_id": part_id, "cycle": cycle, **anomaly_meta},
                )

                # For each machine, emit micro-steps
                for machine in WORKFLOW["machines_order"]:
                    steps = WORKFLOW["micro_steps"][machine]
                    base_durs = split_nominal(machine)

                    # Choose anomaly behavior
                    slow_machine = (is_anomaly and ANOMALY_TYPE == "M2_SLOWDOWN" and machine == "M2")
                    m5_nok = (is_anomaly and ANOMALY_TYPE == "M5_NOK" and machine == "M5")
                    dephasing = (is_anomaly and ANOMALY_TYPE == "DEPHASING" and machine in ("M1", "M2"))

                    # Optional: dephasing means M2 starts late relative to M1.10
                    if dephasing and machine == "M2":
                        extra_delay = 0.6  # seconds (tune)
                        insert_event(
                            cur,
                            ts=utcnow(),
                            part_id=part_id,
                            machine=machine,
                            level="INFO",
                            code="SIM",
                            message=f"DEPHASING_DELAY_{extra_delay:.1f}s",
                            cycle=cycle,
                            step_id="M2.01",
                            step_name="WAIT_M1_READY",
                            duration=extra_delay,
                            payload={"sim": True, "anomaly": True, "delay_s": extra_delay},
                        )
                        sleep_s(extra_delay)

                    for (step_id, step_name), base in zip(steps, base_durs):
                        # jitter
                        jitter = 1.0 + random.uniform(-JITTER_RATIO, JITTER_RATIO)
                        dur = max(base * jitter, 0.05)

                        # anomaly: machine slowdown
                        if slow_machine and (step_id in ("M2.07", "M2.08", "M2.12")):
                            dur *= ANOMALY_MULTIPLIER

                        # Emit INFO step begin-ish event
                        insert_event(
                            c,
                            cur,
                            ts=utcnow(),
                            part_id=part_id,
                            machine=machine,
                            level="INFO",
                            code="STEP",
                            message="STEP",
                            cycle=cycle,
                            step_id=step_id,
                            step_name=step_name,
                            duration=dur,
                            payload={"sim": True, "anomaly": is_anomaly, "base_s": base, "dur_s": dur},
                        )

                        # Optional ERROR injection when slowed down (so downtime can be counted in OEE)
                        if slow_machine and step_id == "M2.08":
                            err_dur = max(dur * 0.3, 0.5)
                            insert_event(
                                c,
                                cur,
                                ts=utcnow(),
                                part_id=part_id,
                                machine=machine,
                                level="ERROR",
                                code="E-M2-011",
                                message="SPINDLE_OVERCURRENT (simulated) - slowdown",
                                cycle=cycle,
                                step_id=step_id,
                                step_name=step_name,
                                duration=err_dur,  # downtime approximation
                                payload={"sim": True, "anomaly": True, "error": "SPINDLE_OVERCURRENT"},
                            )

                        sleep_s(dur)

                        # Emit OK marker (so your dephasing view and live views work)
                        insert_event(
                            c,
                            cur,
                            ts=utcnow(),
                            part_id=part_id,
                            machine=machine,
                            level="OK",
                            code="OK",
                            message="STEP_OK",
                            cycle=cycle,
                            step_id=step_id,
                            step_name=step_name,
                            duration=dur,
                            payload={"sim": True, "anomaly": is_anomaly},
                        )

                    # If M5, emit quality marker
                    if machine == "M5":
                        qmsg = WORKFLOW["m5_nok_message"] if m5_nok else WORKFLOW["m5_ok_message"]
                        insert_event(
                            c,
                            cur,
                            ts=utcnow(),
                            part_id=part_id,
                            machine="M5",
                            level="OK" if not m5_nok else "ERROR",
                            code=qmsg,
                            message=qmsg,
                            cycle=cycle,
                            step_id="M5.11",
                            step_name="LOG_RESULT",
                            duration=0.1,
                            payload={"sim": True, "result": "NOK" if m5_nok else "OK", "anomaly": is_anomaly},
                        )
                        sleep_s(0.1)

                # End-of-cycle marker (used by your /api/oee)
                insert_event(
                    c,
                    cur,
                    ts=utcnow(),
                    part_id=part_id,
                    machine="SYSTEM",
                    level="INFO",
                    code="SIM",
                    message=WORKFLOW["cycle_end_message"],
                    cycle=cycle,
                    step_id="S6",
                    step_name="CYCLE",
                    duration=None,
                    payload={"sim": True, "part_id": part_id, "cycle": cycle, **anomaly_meta},
                )

                cycle += 1


if __name__ == "__main__":
    try:
        run_sim()
    except KeyboardInterrupt:
        print("\nStopped.")
