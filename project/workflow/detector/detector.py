import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from sklearn.ensemble import IsolationForest
from supervision_handler.app.factory import db
from sqlalchemy import text
import json

from supervision_handler.app.models import PlcAnomaly

# ============================================================
# UTILITAIRES WORKFLOW
# ============================================================


def detect_sequence_violation(df_cycle: pd.DataFrame, workflow: dict):
    nominal_machines = workflow["workflow_global"]["ordre_machines"]
    machine_index = {m: i for i, m in enumerate(nominal_machines)}

    last_idx = -1

    for _, row in df_cycle.iterrows():
        machine = row["machine"]
        if machine not in machine_index:
            return row, "unknown_machine"

        idx = machine_index[machine]

        if idx < last_idx:
            return row, "machine_backward"

        if idx > last_idx + 1:
            return row, "machine_skip"

        last_idx = idx

    return None, None


def detect_time_overrun_step(df_cycle: pd.DataFrame, workflow: dict):
    scenario = workflow["scenario_nominal"]["sequence"]

    for block in scenario:
        machine = block["machine"]
        nominal_duration = block["end_at"] - block["start_at"]

        machine_steps = df_cycle[
            (df_cycle["machine"] == machine) &
            (df_cycle["duration"].notna()) &
            (df_cycle["duration"] > 0)
        ]

        if machine_steps.empty:
            continue

        real_duration = machine_steps["duration"].sum()

        # Tolérance 10 %
        print("real_duration ", real_duration , "nominal_duration ", nominal_duration)

        if real_duration > nominal_duration * 1.1:
            return machine_steps.iloc[-1], "machine_time_overrun"

    return None, None



def detect_plc_error_step(df_cycle: pd.DataFrame):
    err = df_cycle[df_cycle["level"] == "ERROR"]
    if not err.empty:
        return err.iloc[0], "plc_error"
    return None, None


def find_anomalous_step(df_cycle: pd.DataFrame, workflow: dict):
    row, reason = detect_plc_error_step(df_cycle)
    if row is not None:
        return row, reason

    row, reason = detect_sequence_violation(df_cycle, workflow)
    if row is not None:
        return row, reason

    row, reason = detect_time_overrun_step(df_cycle, workflow)
    if row is not None:
        return row, reason

    return None, None


def get_nominal_cycle_time(workflow: dict) -> float:
    return workflow["ligne_industrielle"]["cycle_nominal_s"]


def get_last_step_id(workflow: dict) -> str:
    last_machine = workflow["workflow_global"]["ordre_machines"][-1]
    return workflow["machines"][last_machine]["steps"][-1]["id"]


# ============================================================
# FETCH HISTORIQUE STEP
# ============================================================

def fetch_similar_steps(step_id: str, days: int = 30) -> pd.DataFrame:
    sql = """
    SELECT ts, duration
    FROM plc_events
    WHERE step_id = %s
      AND duration IS NOT NULL
      AND ts >= %s
    ORDER BY ts ASC
    LIMIT 100
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return pd.read_sql(sql, db.engine, params=(step_id, since))


# ============================================================
# MÉTRIQUES STATISTIQUES
# ============================================================

def ewma_ratio(values, alpha=0.3):
    values = np.asarray(values, dtype=float)
    if len(values) < 5:
        return None

    base = np.median(values[:3])
    e = base
    for v in values:
        e = alpha * v + (1 - alpha) * e

    return round(e / max(base, 1e-9), 2)


def hawkes_proxy(ts):
    ts = pd.to_datetime(ts).sort_values()
    if len(ts) < 5:
        return None

    inter = np.diff(ts.values.astype("datetime64[s]").astype(np.int64))
    mu, sigma = np.mean(inter), np.std(inter)

    burstiness = (sigma - mu) / (sigma + mu) if mu + sigma > 0 else 0
    rate_ratio = len(ts[-5:]) / max(len(ts), 1)

    return {
        "rate_ratio": round(rate_ratio, 2),
        "burstiness": round(burstiness, 2),
    }


def isolation_score(values):
    if len(values) < 10:
        return 0.0

    X = np.array(values).reshape(-1, 1)
    model = IsolationForest(contamination="auto", random_state=42)
    model.fit(X)

    scores = -model.decision_function(X)
    scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-9)
    return round(scores[-1], 2)


# ============================================================
# SCORE DE SÉVÉRITÉ
# ============================================================

def compute_severity(rule, iso, ewma, hawkes):
    score = 0

    if rule:
        score += 4
    if iso > 0.7:
        score += 2
    if ewma and ewma > 1.3:
        score += 2
    if hawkes and hawkes["rate_ratio"] > 1.5:
        score += 2

    if score >= 7:
        return "CRITICAL"
    if score >= 4:
        return "SERIOUS"
    return "INFO"

def load_cycle_events_by_part(part_id: str) -> pd.DataFrame:
    sql = """
    SELECT
        ts, machine, level, code, message, part_id,
        cycle, step_id, step_name, duration
    FROM plc_events
    WHERE part_id = %s
    ORDER BY ts ASC
    """
    return pd.read_sql(sql, db.engine, params=(part_id,))


def is_cycle_finished(df_cycle: pd.DataFrame, workflow: dict) -> bool:
    if df_cycle.empty:
        return False

    # 1️⃣ ERREUR PLC → cycle terminé immédiatement
    if (
        (df_cycle["level"].eq("ERROR")) |
        (df_cycle["code"].fillna("").str.startswith("E-"))
    ).any():
        return True

    if df_cycle["code"].astype(str).str.startswith("E-").any():
        return True

    # 2️⃣ Dernier step nominal atteint
    last_nominal_step = get_last_step_of_last_machine(workflow)
    last_step_seen = df_cycle.iloc[-1]["step_id"]

    return last_step_seen == last_nominal_step



def get_last_step_of_last_machine(workflow) -> str:
    last_machine = workflow["workflow_global"]["ordre_machines"][-1]
    last_step = workflow["machines"][last_machine]["steps"][-1]["id"]
    return last_step
        

# ============================================================
# DÉTECTEUR PRINCIPAL
# ============================================================
def compute_cycle_duration(df_cycle: pd.DataFrame) -> float:
    """
    Calcule la durée réelle d’un cycle PLC en secondes
    à partir des timestamps des événements.
    """
    if df_cycle is None or df_cycle.empty:
        return 0.0

    # sécurité timestamps
    if "ts" not in df_cycle.columns:
        return 0.0

    ts_min = df_cycle["ts"].min()
    ts_max = df_cycle["ts"].max()

    if pd.isna(ts_min) or pd.isna(ts_max):
        return 0.0

    return (ts_max - ts_min).total_seconds()




def get_last_event(pard_id) -> dict | None:
    """
    Récupère le dernier plc_event inséré en base.
    Retourne un dict Python propre.
    """
    sql = """
    SELECT
        ts,
        part_id,
        machine,
        level,
        code,
        message,
        cycle,
        step_id,
        step_name,
        duration

    FROM plc_events
    WHERE part_id = %s 
    ORDER BY ts DESC

    """

    df = pd.read_sql(sql, db.engine,params=(pard_id,))

    if df.empty:
        return None

    row = df.iloc[0]

    return {
        "ts": row["ts"].to_pydatetime() if pd.notna(row["ts"]) else None,
        "part_id": row.get("part_id"),
        "machine": row.get("machine"),
        "level": row.get("level"),
        "code": row.get("code"),
        "message": row.get("message"),
        "cycle": int(row["cycle"]) if pd.notna(row["cycle"]) else None,
        "step_id": row.get("step_id"),
        "step_name": row.get("step_name"),
        "duration": float(row["duration"]) if pd.notna(row["duration"]) else None,
    }



def detector_anomalies(event, workflow: dict):
    """
    Détection d'anomalie PLC (appelée à chaque nouvel event)
    """

    if not event.get("cycle"):
        return None

    # ======================================================
    # 1) Charger le cycle
    # ======================================================
    df_cycle = load_cycle_events_by_part(event["part_id"])

    if not is_cycle_finished(df_cycle, workflow):
        return None

    # ======================================================
    # 2) Infos cycle
    # ======================================================
    cycle_duration = compute_cycle_duration(df_cycle)
    nominal_cycle = workflow["ligne_industrielle"]["cycle_nominal_s"]
    duration_overrun = max(cycle_duration - nominal_cycle, 0)

    anomaly_step, root_reason = find_anomalous_step(df_cycle, workflow)
    if anomaly_step is None:
        return None

    # ======================================================
    # 3) RÈGLES TERRAIN
    # ======================================================
    rule_anomaly = root_reason in {
        "plc_error",
        "machine_skip",
        "machine_backward",
        "machine_time_overrun",
    }

    # ======================================================
    # 4) HISTORIQUE STEP
    # ======================================================
    hist = fetch_similar_steps(anomaly_step["step_id"])

    ewma = ewma_ratio(hist["duration"]) if not hist.empty else None
    hawkes = hawkes_proxy(hist["ts"]) if not hist.empty else None
    iso = isolation_score(hist["duration"]) if not hist.empty else 0.0

    # ======================================================
    # 5) SÉVÉRITÉ
    # ======================================================
    severity = compute_severity(rule_anomaly, iso, ewma, hawkes)

    if not rule_anomaly and iso < 0.6:
        return None

    # ======================================================
    # 6) INSERT ORM (PROPRE)
    # ======================================================
    try:
        plc_anomaly = PlcAnomaly(
            part_id = event["part_id"],
            event_ts=event["ts"],
            cycle=int(anomaly_step["cycle"]),
            machine=anomaly_step["machine"],
            step_id=anomaly_step.get("step_id"),
            step_name=anomaly_step.get("step_name"),
            n_step_errors = int(df_cycle["level"].eq("ERROR").sum()),
            anomaly_score=float(iso),
            rule_anomaly=rule_anomaly,
            rule_reasons=[root_reason],

            cycle_duration_s=cycle_duration,
            duration_overrun_s=duration_overrun,

            ewma_ratio=float(ewma) if ewma is not None else None,
            rate_ratio=float(hawkes["rate_ratio"]) if hawkes else None,
            burstiness=float(hawkes["burstiness"]) if hawkes else None,
            hawkes_score=int(hawkes["rate_ratio"] > 1.5) if hawkes else 0,

            severity=severity,
            status="CLOSED",
            report_path = (
                datetime.now().strftime("%Y%m%d")
                + "/"
                + f"rapport_llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

        )

        db.session.add(plc_anomaly)
        db.session.commit()

        # 🔑 ID AUTO (déjà présent)
        print("✅ anomaly inserted ORM, id =", plc_anomaly.id)

        return plc_anomaly

    except Exception as e:
        db.session.rollback()
        print("❌ ERROR insert anomalie", e)
        return None
