import os
import time
import random
import datetime as dt
from typing import List, Dict, Set

import psycopg2
from psycopg2.extras import Json


# ============================================================
# DB CONFIG
# ============================================================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "plc")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")


# ============================================================
# SIM CONFIG (code-only)
# ============================================================
SPEED_FACTOR = 1.0      # vitesse d'affichage (UI uniquement)
JITTER_RATIO = 0.10     # +/- 50% sur les durées


# ============================================================
# ANOMALY CONFIG (code-only)
# ============================================================
ANOMALY_MODE = "M2_SLOWDOWN"
# "NONE" | "M2_SLOWDOWN" | "M5_NOK" | "DEPHASING"

ANOMALY_EVERY_N_CYCLES = 1
ANOMALY_MULTIPLIER = 2.0
FORCE_ERROR = True


# ============================================================
# MODE SCENARIO (optionnel)
# ============================================================
SCENARIO_ENABLED = True

SCENARIO: Dict[int, List[str]] = {
    1: ["NONE"],
    2: ["M2_SLOWDOWN"],
    3: ["M5_NOK"],
    4: ["DEPHASING"],
    5: ["M2_SLOWDOWN", "DEPHASING"],
}

VALID_ANOMALIES = {"NONE", "M2_SLOWDOWN", "M5_NOK", "DEPHASING"}


# ============================================================
# SIM CLOCK (horloge simulée)
# ============================================================
class SimClock:
    def __init__(self, start_ts: dt.datetime):
        self.current = start_ts

    def now(self) -> dt.datetime:
        return self.current

    def advance(self, seconds: float):
        self.current += dt.timedelta(seconds=float(seconds))


# ============================================================
# WORKFLOW
# ============================================================
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
    "cycle_end_message": "CYCLE_END",
    "m5_ok_message": "M5_OK",
    "m5_nok_message": "M5_NOK",
}

DEFAULT_STEP_WEIGHTS = {
    "WAIT": 0.05, "CHECK": 0.06, "LOCK": 0.05, "RAMP": 0.06, "ON": 0.03,
    "APPROACH": 0.05, "PASS": 0.18, "EXEC": 0.18, "RETRACT": 0.06,
    "CLEAN": 0.05, "SIGNAL": 0.03, "MEASURE": 0.12, "COMPARE": 0.10,
    "ACQ": 0.08, "TRIGGER": 0.04, "UNLOAD": 0.08, "UNCLAMP": 0.05,
    "ALIGN": 0.07, "CLAMP": 0.06, "READ": 0.05, "DETECT": 0.05,
    "TOOL": 0.05, "CHIP": 0.05, "PROBE": 0.06, "TORQUE": 0.06,
    "DEBURR": 0.05, "FEATURE": 0.10,
}


# ============================================================
# UTIL
# ============================================================
def sleep_s(seconds: float):
    time.sleep(max(seconds / max(SPEED_FACTOR, 1e-9), 0.0))


def conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )


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


def active_modes_for_cycle(cycle: int) -> Set[str]:
    if SCENARIO_ENABLED:
        modes = set(SCENARIO.get(cycle, ["NONE"]))
    else:
        modes = {ANOMALY_MODE} if (ANOMALY_MODE != "NONE" and cycle % ANOMALY_EVERY_N_CYCLES == 0) else {"NONE"}

    invalid = modes - VALID_ANOMALIES
    if invalid:
        raise ValueError(f"Invalid anomaly modes: {invalid}")

    if "NONE" in modes and len(modes) > 1:
        modes.remove("NONE")

    return modes


# ============================================================
# SQL
# ============================================================
INSERT_SQL = """
INSERT INTO plc_events (ts, part_id, machine, level, code, message, cycle, step_id, step_name, duration, payload)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def insert_event(c, cur, *, ts, part_id, machine, level, code, message,
                 cycle, step_id, step_name, duration, payload):
    cur.execute(
        INSERT_SQL,
        (
            ts, part_id, machine, level, code, message,
            cycle, step_id, step_name, duration,
            Json(payload) if payload is not None else None
        )
    )
    c.commit()
    print("insert", ts, machine, level, code, step_id)

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
def run_sim():
    print("=== Production simulator started ===")

    cycle = 1
    part_seq = 1

    with conn() as c:
        c.autocommit = True
        with c.cursor() as cur:
            
            clear_db(c,cur)

            while True:
                part_id = f"P{part_seq:06d}"
                part_seq += 1

                insert_part(c,cur,part_id)
                clock = SimClock(dt.datetime.now(dt.timezone.utc))

                modes = active_modes_for_cycle(cycle)
                is_anomaly = ("NONE" not in modes)

                insert_event(
                    c, cur,
                    ts=clock.now(),
                    part_id=part_id,
                    machine="SYSTEM",
                    level="INFO",
                    code="SIM",
                    message="CYCLE_START",
                    cycle=cycle,
                    step_id="S1",
                    step_name="CYCLE",
                    duration=None,
                    payload={"modes": list(modes)},
                )

                for machine in WORKFLOW["machines_order"]:
                    steps = WORKFLOW["micro_steps"][machine]
                    base_durs = split_nominal(machine)

                    slow_machine = ("M2_SLOWDOWN" in modes) and machine == "M2"
                    m5_nok = ("M5_NOK" in modes) and machine == "M5"
                    dephasing = ("DEPHASING" in modes) and machine in ("M1", "M2")

                    if  machine == "M2":
                        delay = 0.6
                        insert_event(
                            c, cur,
                            ts=clock.now(),
                            part_id=part_id,
                            machine=machine,
                            level="INFO",
                            code="SIM",
                            message="DEPHASING_DELAY",
                            cycle=cycle,
                            step_id="M2.01",
                            step_name="WAIT_M1_READY",
                            duration=delay,
                            payload={"delay_s": delay},
                        )
                        clock.advance(delay)
                        sleep_s(delay)

                    for (step_id, step_name), base in zip(steps, base_durs):
                        dur = max(base * (1 + random.uniform(-JITTER_RATIO, JITTER_RATIO)), 0.05)

                        if slow_machine and step_id in ("M2.07", "M2.08", "M2.12"):
                            dur *= ANOMALY_MULTIPLIER

                        insert_event(
                            c, cur,
                            ts=clock.now(),
                            part_id=part_id,
                            machine=machine,
                            level="INFO",
                            code="STEP",
                            message="STEP",
                            cycle=cycle,
                            step_id=step_id,
                            step_name=step_name,
                            duration=dur,
                            payload={"anomaly": is_anomaly},
                        )

                        if FORCE_ERROR and slow_machine and step_id in ("M2.07", "M2.08"):
                            err = max(dur * 0.3, 0.5)
                            insert_event(
                                c, cur,
                                ts=clock.now(),
                                part_id=part_id,
                                machine=machine,
                                level="ERROR",
                                code="E-M2-011",
                                message="SPINDLE_OVERCURRENT",
                                cycle=cycle,
                                step_id=step_id,
                                step_name=step_name,
                                duration=err,
                                payload={"error": True},
                            )
                            clock.advance(err)
                            sleep_s(err)

                        clock.advance(dur)
                        sleep_s(dur)

                        insert_event(
                            c, cur,
                            ts=clock.now(),
                            part_id=part_id,
                            machine=machine,
                            level="OK",
                            code="OK",
                            message="STEP_OK",
                            cycle=cycle,
                            step_id=step_id,
                            step_name=step_name,
                            duration=dur,
                            payload={},
                        )

                    if machine == "M5":
                        q = WORKFLOW["m5_nok_message"] if m5_nok else WORKFLOW["m5_ok_message"]
                        insert_event(
                            c, cur,
                            ts=clock.now(),
                            part_id=part_id,
                            machine="M5",
                            level="ERROR" if m5_nok else "OK",
                            code=q,
                            message=q,
                            cycle=cycle,
                            step_id="M5.11",
                            step_name="LOG_RESULT",
                            duration=0.1,
                            payload={},
                        )
                        clock.advance(0.1)
                        sleep_s(0.1)

                insert_event(
                    c, cur,
                    ts=clock.now(),
                    part_id=part_id,
                    machine="SYSTEM",
                    level="INFO",
                    code="SIM",
                    message=WORKFLOW["cycle_end_message"],
                    cycle=cycle,
                    step_id="S6",
                    step_name="CYCLE",
                    duration=None,
                    payload={},
                )

                cycle += 1


if __name__ == "__main__":
    try:
        run_sim()
    except KeyboardInterrupt:
        print("Stopped.")
