import psycopg2
import pandas as pd
import json
import os
import sys
from supervision_handler.app.factory import socketio,db

# ============================================================
# FETCH EVENTS (BRUTS)
# ============================================================

def fetch_last_event():
    """
    Récupère les événements PLC bruts.
    Aucun calcul métier ici.
    """
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

    sql += " ORDER BY ts DESC limit 1"

    df = pd.read_sql(sql, db.engine)

    if df.empty:
        return df

    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["cycle"] = df["cycle"].astype(int)

    return df.reset_index(drop=True)


def fetch_events_df(param):
    """
    Récupère les événements PLC bruts.
    Aucun calcul métier ici.
    """

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

    df = pd.read_sql(sql, db, params=params)


    if df.empty:
        return df

    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["cycle"] = df["cycle"].astype(int)

    return df.reset_index(drop=True)



def emit_anomalies_df(df, channel="plc_anomaly"):
    """
    Émet des anomalies enrichies (cycle + step + ML + prédiction).
    """
    if df is None or df.empty:
        return

    # Nettoyage / normalisation pour le front
    records = []

    for _, row in df.iterrows():
        records.append({
            # Identité
            "cycle": int(row.get("cycle")),
            "machine": row.get("machine"),
            "step_id": row.get("step_id"),
            "step_name": row.get("step_name"),

            # Détection
            "anomaly_score": float(row.get("anomaly_score", 0)),
            "rule_anomaly": bool(row.get("rule_anomaly", False)),
            "rule_reasons": row.get("rule_reasons", []),

            # STEP
            "has_step_error": bool(row.get("has_step_error", False)),
            "n_step_errors": int(row.get("n_step_errors", 0)),

            # Cycle
            "cycle_duration_s": float(row.get("cycle_duration_s", 0)),
            "duration_overrun_s": float(row.get("duration_overrun_s", 0)),

            # 🔮 Prédictif (optionnel)
            "prediction": {
                "events_count": row.get("events_count"),
                "window_days": row.get("window_days"),
                "confidence": row.get("confidence"),
                "ewma_ratio": row.get("ewma_ratio"),
                "rate_ratio": row.get("rate_ratio"),
                "burstiness": row.get("burstiness"),
                "hawkes_score": row.get("hawkes_score"),
            } if not pd.isna(row.get("events_count")) else None,
        })

    payload = {
        "count": len(records),
        "anomalies": records
    }

    socketio.emit(
        channel,
        payload,
        namespace="/"
    )
    
    
def fetch_events_df_with_groupby(param, period: str = "day"):
    if period != "day":
        raise ValueError("Cette implémentation est dédiée à period='day'")

    if not param.get("start") or not param.get("end"):
        raise ValueError("start et end sont obligatoires")

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

    df = pd.read_sql(sql, db, params=params)

    df["period_day"] = pd.to_datetime(df["period_day"])
    return df.reset_index(drop=True)



def project_step_to_cycle(step_df: pd.DataFrame) -> pd.DataFrame:
    """
    Projette les informations STEP au niveau cycle.
    Le `code` retenu est le dernier code d'erreur STEP du cycle.
    """

    agg = (
        step_df
        .groupby(["cycle", "machine"])
        .agg(
            has_step_error=("has_step_error", "max"),
            n_step_errors=("has_step_error", "sum"),
            max_step_duration=("step_duration_s", "max"),
            sum_step_duration=("step_duration_s", "sum"),
            faulty_step_id=("step_id", "last"),
            code=("code", lambda s: s.dropna().iloc[-1] if not s.dropna().empty else None)
        )
        .reset_index()
    )

    return agg


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

def build_step_features(df_events: pd.DataFrame) -> pd.DataFrame:
    """
    Construit les features STEP à partir des événements PLC.
    NE MODIFIE PAS la logique cycle existante.
    """

    df = df_events.copy()

    # --- GARANTIES MINIMALES (NON DESTRUCTIVES) ---
    if "code" not in df.columns:
        df["code"] = None

    if "level" not in df.columns:
        df["level"] = None

    # --- ERREUR STEP (booléen simple) ---
    df["has_step_error"] = (
        df["level"].isin(["ERROR", "ALARM"])
        | df["code"].notna()
    )

    # --- AGRÉGATION IDENTIQUE À TON DESIGN ---
    step_df = (
        df
        .groupby(["cycle", "machine", "step_id"], dropna=False)
        .agg(
            step_duration_s=("duration", "sum"),
            has_step_error=("has_step_error", "max"),
            code=("code", "last"),
        )
        .reset_index()
    )

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

    # --- PARAMÈTRES INDUSTRIELS ---
    CYCLE_DRIFT_S = 10          # dérive cycle absolue (secondes)
    CYCLE_DRIFT_PCT = 0.20      # dérive cycle relative (20%)

    df["rule_anomaly"] = False
    df["rule_reasons"] = [[] for _ in range(len(df))]
    df["severity"] = "OK"

    for idx, row in df.iterrows():
        reasons = []

        # ==================================================
        # 1️⃣ ERREURS STEP / PLC → ANOMALIE DIRECTE
        # ==================================================
        if row.get("n_errors", 0) > 0:
            reasons.append("plc_error_present")

        if row.get("delta_steps", 0) != 0:
            reasons.append("step_count_mismatch")

        if row.get("machine_order") != row.get("expected_machine_order"):
            reasons.append("grafcet_order_violation")
            
        if row.get("has_step_error", False):
            reasons.append("step_error")

        # 👉 Si une erreur STEP existe → anomalie immédiate
        if reasons:
            df.at[idx, "rule_anomaly"] = True
            df.at[idx, "rule_reasons"] = reasons
            df.at[idx, "severity"] = "STEP_ERROR"
            continue

        # ==================================================
        # 2️⃣ ÉCART CYCLE → ANOMALIE SI SEUIL
        # ==================================================
        delta_cycle_s = abs(row.get("cycle_delta_s", 0))
        delta_cycle_pct = abs(row.get("delta_duration_ratio", 0))

        if delta_cycle_s > CYCLE_DRIFT_S or delta_cycle_pct > CYCLE_DRIFT_PCT:
            df.at[idx, "rule_anomaly"] = True
            df.at[idx, "rule_reasons"] = ["cycle_duration_drift"]
            df.at[idx, "severity"] = "CYCLE_DRIFT"
            continue

        # ==================================================
        # 3️⃣ SINON → PAS ANOMALIE
        # ==================================================
        df.at[idx, "rule_reasons"] = []

    return df
