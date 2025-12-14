
# feature_builder.py
# Extraction des features time-series depuis PostgreSQL / TimescaleDB

import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import pandas as pd

import os.path as op
import os
import sys
import json 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config_plc import DB_CONFIG, N_LAST_CYCLES

WORKFLOW_RESSOURCE=""

def connect_db():
    return psycopg2.connect(**DB_CONFIG)


import pandas as pd

def add_duration_overrun(features_df, workflow_json):
    """
    Ajoute la colonne duration_overrun_s :
    dépassement réel vs cycle nominal du workflow
    """
    workflow = parse_workflow(workflow_json)
    nominal_cycle_s = workflow["cycle_nominal_s"]

    # Sécurité : colonne réelle existante ?
    if "cycle_duration_s" not in features_df.columns:
        raise ValueError("cycle_duration_s manquant dans features_df")

    # Calcul du dépassement (jamais négatif)
    features_df["duration_overrun_s"] = (
        features_df["cycle_duration_s"] - nominal_cycle_s
    ).clip(lower=0)

    return features_df


def fetch_events_df(param):
    """
    Récupère les événements PLC bruts en DataFrame.
    Ces données sont destinées à être agrégées ensuite
    (par cycle / machine / step).
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

        # -------------------------------
        # Filtre temporel
        # -------------------------------
        if param.get("start") and param.get("end"):
            sql += " AND ts BETWEEN %s AND %s"
            params.extend([param["start"], param["end"]])
        elif param.get("start"):
            sql += " AND ts >= %s"
            params.append(param["start"])
        elif param.get("end"):
            sql += " AND ts <= %s"
            params.append(param["end"])

        # -------------------------------
        # Filtre pièce
        # -------------------------------
        if param.get("part_id"):
            sql += " AND part_id = %s"
            params.append(param["part_id"])

        # -------------------------------
        # Filtre machine
        # -------------------------------
        if param.get("ligne"):
            sql += " AND machine = %s"
            params.append(param["ligne"])

        # -------------------------------
        # Ordre strict (CRUCIAL pour latences)
        # -------------------------------
        sql += " ORDER BY cycle ASC, ts ASC"

        df = pd.read_sql(sql, conn, params=params)

    finally:
        conn.close()

    if df.empty:
        return df

    # Typage & sécurité
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["cycle"] = df["cycle"].astype(int)

    return df.reset_index(drop=True)



def parse_workflow(workflow_json: str) -> dict:
    wf = json.loads(workflow_json)

    cycle_nominal = wf["ligne_industrielle"]["cycle_nominal_s"]
    machine_order = wf["workflow_global"]["ordre_machines"]
    nominal_durations = wf["workflow_global"]["durees_nominales_s"]

    # Nombre de steps par machine (Grafcet machine)
    steps_per_machine = {}
    for m, data in wf["machines"].items():
        steps_per_machine[m] = len(data.get("steps", []))

    return {
        "cycle_nominal_s": cycle_nominal,
        "machine_order": machine_order,
        "nominal_durations": nominal_durations,
        "steps_per_machine": steps_per_machine,
    }

import pandas as pd

def add_nominal_deviation(
    features: pd.DataFrame,
    workflow_json: str
) -> pd.DataFrame:
    """
    Compare les données réelles au scénario nominal décrit dans le workflow JSON.
    """
    wf = parse_workflow(workflow_json)
    df = features.copy()

    # Nominal machine
    df["nominal_duration_s"] = df["machine"].map(
        wf["nominal_durations"]
    )

    df["nominal_steps"] = df["machine"].map(
        wf["steps_per_machine"]
    )

    # Écarts machine
    df["delta_duration_s"] = df["duration_s"] - df["nominal_duration_s"]
    df["delta_duration_ratio"] = (
        df["delta_duration_s"] / df["nominal_duration_s"]
    )

    df["delta_steps"] = df["n_steps"] - df["nominal_steps"]

    # Écart cycle global
    df["cycle_delta_s"] = (
        df["cycle_duration_s"] - wf["cycle_nominal_s"]
    )

    # Ordre machine attendu (Grafcet)
    expected_order = {
        m: i + 1 for i, m in enumerate(wf["machine_order"])
    }
    df["expected_machine_order"] = df["machine"].map(expected_order)

    return df

def rule_based_anomalies(
    features: pd.DataFrame,
    workflow_json: str
) -> pd.DataFrame:
    """
    Détection déterministe d'anomalies industrielles
    basée uniquement sur le workflow fourni.
    """
    wf = parse_workflow(workflow_json)
    df = features.copy()

    rules = {}

    # 1️⃣ Durée machine hors tolérance (+/-20%)
    rules["duration_out_of_nominal"] = (
        df["delta_duration_ratio"].abs() > 0.20
    )

    # 2️⃣ Incohérence de steps (Grafcet machine)
    rules["step_count_mismatch"] = df["delta_steps"] != 0

    # 3️⃣ Présence d'erreurs PLC
    rules["plc_error_present"] = df["n_errors"] > 0

    # 4️⃣ Dérive cycle global (+/-10s)
    rules["cycle_duration_drift"] = (
        df["cycle_delta_s"].abs() > 10
    )

    # 5️⃣ Violation ordre Grafcet inter-machines
    rules["grafcet_order_violation"] = (
        df["machine_order"] != df["expected_machine_order"]
    )

    rules_df = pd.DataFrame(rules)

    df["rule_anomaly"] = rules_df.any(axis=1)

    # Raisons explicites → clé pour le LLM
    df["rule_reasons"] = rules_df.apply(
        lambda r: [k for k, v in r.items() if v],
        axis=1
    )

    return df


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

    # Durée machine
    features["duration_s"] = (
        features["ts_end"] - features["ts_start"]
    ).dt.total_seconds()

    # Nombre de steps distincts
    step_counts = (
        df.groupby(["cycle", "machine"])["step_id"]
        .nunique()
        .reset_index(name="n_steps")
    )
    features = features.merge(
        step_counts, on=["cycle", "machine"], how="left"
    )

    # Ordre machine
    machine_order_map = {"M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5}
    features["machine_order"] = (
        features["machine"].map(machine_order_map).fillna(0)
    )

    # Durée cycle globale
    cycle_span = df.groupby("cycle").agg(
        cycle_ts_start=("ts", "min"),
        cycle_ts_end=("ts", "max"),
    ).reset_index()
    cycle_span["cycle_duration_s"] = (
        cycle_span["cycle_ts_end"] - cycle_span["cycle_ts_start"]
    ).dt.total_seconds()

    features = features.merge(
        cycle_span[["cycle", "cycle_duration_s"]],
        on="cycle",
        how="left"
    )

    return features
