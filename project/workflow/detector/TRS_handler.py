import os
import psycopg2
from datetime import datetime
from config_plc import DB_CONFIG
from feature_handler import parse_workflow


# ============================================================
# DB
# ============================================================

def connect_db():
    return psycopg2.connect(**DB_CONFIG)


# ============================================================
# FETCH REAL CYCLES (1 cycle = 1 pièce)
# ============================================================

def fetch_cycles_data(conn, start: datetime, end: datetime):
    """
    Retourne les cycles réels sur l'intervalle
    - start_ts : premier event du cycle
    - end_ts   : dernier event du cycle
    - has_error: au moins une erreur sur le cycle
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                cycle,
                MIN(ts) AS start_ts,
                MAX(ts) AS end_ts,
                BOOL_OR(level = 'ERROR') AS has_error
            FROM plc_events
            WHERE ts BETWEEN %s AND %s
              AND cycle IS NOT NULL
            GROUP BY cycle
            ORDER BY start_ts
        """, (start, end))

        rows = cur.fetchall()

    return [
        {
            "cycle": r[0],
            "start_ts": r[1],
            "end_ts": r[2],
            "has_error": r[3],
        }
        for r in rows
        if r[1] is not None and r[2] is not None
    ]


# ============================================================
# WORKFLOW THEORETICAL CYCLE
# ============================================================

def compute_theoretical_cycle(workflow: dict) -> float:
    """
    Calcule le cycle théorique du workflow à partir du scénario nominal
    """
    machine_order = workflow["machine_order"]
    nominal_durations = workflow["nominal_durations"]

    cycle_theoretical_s = 0.0

    for machine in machine_order:
        if machine not in nominal_durations:
            raise ValueError(f"Durée nominale manquante pour {machine}")
        cycle_theoretical_s += float(nominal_durations[machine])

    # buffers optionnels
    if "buffers" in nominal_durations:
        cycle_theoretical_s += float(nominal_durations["buffers"])

    return cycle_theoretical_s


# ============================================================
# TRS CALCULATION (WORKFLOW-DRIVEN)
# ============================================================

def calculate_trs(workflow: str, start: datetime, end: datetime):
    """
    TRS = Disponibilité × Performance × Qualité
    Basé strictement sur le workflow nominal
    """

    # ---------------------------
    # Workflow nominal
    # ---------------------------
    workflow = parse_workflow(workflow)
    cycle_theoretical_s = compute_theoretical_cycle(workflow)

    # ---------------------------
    # Fetch real data
    # ---------------------------
    conn = connect_db()
    try:
        cycles_data = fetch_cycles_data(conn, start, end)
    finally:
        conn.close()

    total_cycles = len(cycles_data)
    if total_cycles == 0:
        return {
            "trs": 0.0,
            "reason": "no production",
            "cycle_theoretical_s": cycle_theoretical_s
        }

    # ---------------------------
    # Real metrics
    # ---------------------------
    total_real_time = 0.0
    good_cycles = 0

    for c in cycles_data:
        real_time = (c["end_ts"] - c["start_ts"]).total_seconds()
        if real_time > 0:
            total_real_time += real_time
        if not c["has_error"]:
            good_cycles += 1

    if total_real_time <= 0:
        return {"error": "no measurable runtime"}

    # ---------------------------
    # TRS components
    # ---------------------------

    performance = min(
        (total_cycles * cycle_theoretical_s) / total_real_time,
        1.0
    )

    quality = good_cycles / total_cycles

    trs =  performance * quality

    # ---------------------------
    # Result
    # ---------------------------
    return {
        "performance": round(performance, 4),
        "quality": round(quality, 4),
        "trs": round(trs, 4),
        "total_cycles": total_cycles,
        "good_cycles": good_cycles,
        "bad_cycles": total_cycles - good_cycles,
        "cycle_theoretical_s": round(cycle_theoretical_s, 2),
        "real_time_s": round(total_real_time, 2),
    }
