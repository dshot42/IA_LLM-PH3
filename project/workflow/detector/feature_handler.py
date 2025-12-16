# feature_builder.py
# Extraction et agrégation des features PLC (TimescaleDB)
# Architecture :
# - Events bruts
# - Features STEP (preuve terrain)
# - Features CYCLE (ML / règles)
# - Calculs d’impact (Python only)

import psycopg2
import pandas as pd
import json
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from supervision_handler.app.factory import socketio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config_plc import DB_CONFIG


# ============================================================
# DATABASE
# ============================================================

def connect_db():
    return psycopg2.connect(**DB_CONFIG)


# ============================================================
# FETCH EVENTS (BRUTS)
# ============================================================

def fetch_events_df(param):
    """
    Récupère les événements PLC bruts.
    Aucun calcul métier ici.
    """
    conn = connect_db()
    try:
        sql = """
        SELECT
            ts,
            machine,
            level,
            code,
            message,
            cycle,
            step_id,
            step_name,
            duration
        FROM plc_events
        WHERE cycle IS NOT NULL
        """

        params = []

        if param.get("start") and param.get("end"):
            sql += " AND ts BETWEEN %s AND %s"
            params.extend([param["start"], param["end"]])
        elif param.get("start"):
            sql += " AND ts >= %s"
            params.append(param["start"])
        elif param.get("end"):
            sql += " AND ts <= %s"
            params.append(param["end"])

        if param.get("part_id"):
            sql += " AND part_id = %s"
            params.append(param["part_id"])

        if param.get("ligne"):
            sql += " AND machine = %s"
            params.append(param["ligne"])

        sql += " ORDER BY cycle ASC, ts ASC"

        df = pd.read_sql(sql, conn, params=params)

    finally:
        conn.close()

    if df.empty:
        return df

    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["cycle"] = df["cycle"].astype(int)

    return df.reset_index(drop=True)



def emit_events_df(df, channel="plc_event"):
    if df.empty:
        return

    payload = {
        "count": len(df),
        "events": df.to_dict(orient="records")
    }

    socketio.emit(
        channel,
        payload,
        namespace="/"   # ou "/" si tu n’utilises pas de namespace
    )
    
def fetch_events_df_with_groupby(param, period: str = "day"):
    if period != "day":
        raise ValueError("Cette implémentation est dédiée à period='day'")

    if not param.get("start") or not param.get("end"):
        raise ValueError("start et end sont obligatoires")

    conn = connect_db()
    try:
        params = [
            param["start"],
            param["end"],
            param["start"],
            param["end"],
        ]

        sql = """
        WITH days AS (
            SELECT generate_series(
                %s::date,
                %s::date,
                INTERVAL '1 day'
            ) AS day
        ),
        steps AS (
            SELECT DISTINCT
                step_id,
                step_name,
                machine
            FROM plc_events
        ),
        grid AS (
            SELECT
                d.day,
                s.machine,
                s.step_id,
                s.step_name
            FROM days d
            CROSS JOIN steps s
        ),
        events AS (
            SELECT
                ts::date AS day,
                machine,
                step_id,
                step_name,
                COUNT(*) AS event_count,
                SUM(duration) AS total_duration
            FROM plc_events
            WHERE cycle IS NOT NULL
              AND ts BETWEEN %s AND %s
        """

        if param.get("ligne"):
            sql += " AND machine = %s"
            params.append(param["ligne"])

        sql += """
            GROUP BY
                day,
                machine,
                step_id,
                step_name
        )
        SELECT
            g.day AS period_day,
            g.machine,
            g.step_id,
            g.step_name,
            COALESCE(e.event_count, 0) AS event_count,
            COALESCE(e.total_duration, 0) AS total_duration
        FROM grid g
        LEFT JOIN events e
            ON e.day = g.day
           AND e.machine = g.machine
           AND e.step_id = g.step_id
        ORDER BY
            g.day ASC,
            g.step_id ASC
        """

        df = pd.read_sql(sql, conn, params=params)

    finally:
        conn.close()

    df["period_day"] = pd.to_datetime(df["period_day"])
    return df.reset_index(drop=True)


# ============================================================
# WORKFLOW PARSING
# ============================================================

def parse_workflow(workflow_json: str) -> dict:
    wf = json.loads(workflow_json)

    cycle_nominal = wf["ligne_industrielle"]["cycle_nominal_s"]
    machine_order = wf["workflow_global"]["ordre_machines"]
    nominal_durations = wf["workflow_global"]["durees_nominales_s"]

    steps_per_machine = {
        m: len(data.get("steps", []))
        for m, data in wf["machines"].items()
    }

    return {
        "cycle_nominal_s": cycle_nominal,
        "machine_order": machine_order,
        "nominal_durations": nominal_durations,
        "steps_per_machine": steps_per_machine,
    }


# ============================================================
# STEP-LEVEL FEATURES (NOUVEL ÉTAGE)
# ============================================================

def build_step_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrégation réelle par STEP (cycle / machine / step).
    Base factuelle READY / DONE / synchronisation.
    """
    if df.empty:
        return df

    grp = df.groupby(
        ["cycle", "machine", "step_id", "step_name"],
        as_index=False
    )

    step_df = grp.agg(
        ts_start=("ts", "min"),
        ts_end=("ts", "max"),
        n_events=("ts", "count"),
        n_errors=("level", lambda s: (s == "ERROR").sum()),
    )

    step_df["step_duration_s"] = (
        step_df["ts_end"] - step_df["ts_start"]
    ).dt.total_seconds()

    return step_df



# ============================================================
# CYCLE-LEVEL FEATURES (EXISTANT, INCHANGÉ)
# ============================================================

def build_cycle_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    grp = df.groupby(["cycle", "machine"])

    features = grp.agg(
        ts_start=("ts", "min"),
        ts_end=("ts", "max"),
        n_events=("ts", "count"),
        n_errors=("level", lambda s: (s == "ERROR").sum()),
        step_id=("step_id", "last"),
        step_name=("step_name", "last"),
        level=("level", "last"),
    ).reset_index()

    features["duration_s"] = (
        features["ts_end"] - features["ts_start"]
    ).dt.total_seconds()

    step_counts = (
        df.groupby(["cycle", "machine"])["step_id"]
        .nunique()
        .reset_index(name="n_steps")
    )

    features = features.merge(
        step_counts, on=["cycle", "machine"], how="left"
    )

    machine_order_map = {"M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5}
    features["machine_order"] = (
        features["machine"].map(machine_order_map).fillna(0)
    )

    cycle_span = df.groupby("cycle").agg(
        cycle_ts_start=("ts", "min"),
        cycle_ts_end=("ts", "max"),
    ).reset_index()

    cycle_span["cycle_duration_s"] = (
        cycle_span["cycle_ts_end"] - cycle_span["cycle_ts_start"]
    ).dt.total_seconds()

    return features.merge(
        cycle_span[["cycle", "cycle_duration_s"]],
        on="cycle",
        how="left"
    )


# ============================================================
# NOMINAL COMPARISON
# ============================================================

def add_nominal_deviation(features: pd.DataFrame, workflow_json: str) -> pd.DataFrame:
    wf = parse_workflow(workflow_json)
    df = features.copy()

    df["nominal_duration_s"] = df["machine"].map(wf["nominal_durations"])
    df["nominal_steps"] = df["machine"].map(wf["steps_per_machine"])

    df["delta_duration_s"] = df["duration_s"] - df["nominal_duration_s"]
    df["delta_duration_ratio"] = df["delta_duration_s"] / df["nominal_duration_s"]
    df["delta_steps"] = df["n_steps"] - df["nominal_steps"]

    df["cycle_delta_s"] = df["cycle_duration_s"] - wf["cycle_nominal_s"]

    expected_order = {
        m: i + 1 for i, m in enumerate(wf["machine_order"])
    }
    df["expected_machine_order"] = df["machine"].map(expected_order)

    return df


def add_duration_overrun(features_df: pd.DataFrame, workflow_json: str) -> pd.DataFrame:
    wf = parse_workflow(workflow_json)

    features_df["duration_overrun_s"] = (
        features_df["cycle_duration_s"] - wf["cycle_nominal_s"]
    ).clip(lower=0)

    return features_df


# ============================================================
# RULE-BASED ANOMALIES (INCHANGÉ)
# ============================================================

def rule_based_anomalies(features: pd.DataFrame, workflow_json: str) -> pd.DataFrame:
    df = features.copy()

    rules = {
        "duration_out_of_nominal": df["delta_duration_ratio"].abs() > 0.20,
        "step_count_mismatch": df["delta_steps"] != 0,
        "plc_error_present": df["n_errors"] > 0,
        "cycle_duration_drift": df["cycle_delta_s"].abs() > 10,
        "grafcet_order_violation": df["machine_order"] != df["expected_machine_order"],
    }

    rules_df = pd.DataFrame(rules)

    df["rule_anomaly"] = rules_df.any(axis=1)
    df["rule_reasons"] = rules_df.apply(
        lambda r: [k for k, v in r.items() if v], axis=1
    )

    return df
