import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from sklearn.ensemble import IsolationForest
from supervision_handler.app.factory import db

# ============================================================
# SEVERITY & CONFIDENCE
# ============================================================

SEVERITY_ORDER = {
    "OK": 0,
    "NO_HISTORY": 1,
    "WARNING": 2,
    "MAJOR": 3,
    "CRITICAL": 4,
}

CONFIDENCE_LEVELS = {
    "insufficient": 0.0,
    "low": 0.3,
    "medium": 0.6,
    "high": 1.0,
}

def confidence_label(n_events: int) -> str:
    if n_events >= 30:
        return "high"
    if n_events >= 20:
        return "medium"
    if n_events >= 10:
        return "low"
    return "insufficient"


# ============================================================
# STATISTIQUES
# ============================================================

def ewma_ratio(values, alpha=0.3):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]

    if len(values) < 3:
        return None

    base = np.median(values[:3])
    e = base
    for v in values:
        e = alpha * v + (1 - alpha) * e

    return round(e / max(base, 1e-9), 2)


def hawkes_proxy(ts):
    ts = pd.to_datetime(ts, utc=True).sort_values()
    if len(ts) < 3:
        return None

    inter = np.diff(ts.values.astype("datetime64[s]").astype(np.int64))
    mu, sigma = np.mean(inter), np.std(inter)
    burstiness = (sigma - mu) / (sigma + mu) if mu + sigma > 0 else 0.0

    total_rate = len(ts) / max((ts.iloc[-1] - ts.iloc[0]).total_seconds(), 1)
    recent = ts.iloc[int(len(ts) * 0.7):]
    recent_rate = len(recent) / max((recent.iloc[-1] - recent.iloc[0]).total_seconds(), 1)

    return {
        "rate_ratio": round(recent_rate / total_rate, 2),
        "burstiness": round(burstiness, 2),
    }


# ============================================================
# SQL HISTORIQUE STEP
# ============================================================

def fetch_step_history(machine, step_id, min_events=10, max_days=30):
    now = datetime.now(timezone.utc)
    last_df = None

    for days in range(3, max_days + 1, 2):
        since = now - timedelta(days=days)

        df = pd.read_sql(
            """
            SELECT ts, duration
            FROM plc_events
            WHERE machine = %s
              AND step_id = %s
              AND ts >= %s
              AND duration IS NOT NULL
            ORDER BY ts ASC
            """,
            db.engine,
            params=(machine, step_id, since),
        )

        if not df.empty:
            df = df.copy()
            df["window_days"] = days
            last_df = df

            if len(df) >= min_events:
                return df

    return last_df


# ============================================================
# ML STEP LEVEL
# ============================================================

def isolation_forest_scores(values):
    if len(values) < 10:
        return None

    X = values.reshape(-1, 1)
    model = IsolationForest(
        n_estimators=100,
        contamination="auto",
        random_state=42,
    )
    model.fit(X)

    scores = -model.decision_function(X)
    scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-9)
    return scores


# ============================================================
# MAIN PREDICTION — ANOMALY IN → ANOMALY ENRICHED
# ============================================================

def compute_prediction(anomaly: dict) -> dict:
    """
    Enrichit UNE anomalie PLC existante avec du prédictif.
    Input = ligne plc_anomalies (dict)
    """

    result = {
        "events_count": 0,
        "window_days": None,
        "confidence": "insufficient",
        "ewma_ratio": None,
        "rate_ratio": None,
        "burstiness": None,
        "hawkes_score": 0,
        "anomaly_score": anomaly.anomaly_score or 0.0,
        "severity": anomaly.severity or"NO_HISTORY",
    }

    machine = anomaly.machine
    step_id = anomaly.step_id

    if not machine or not step_id:
        return result

    hist = fetch_step_history(machine, step_id)
    if hist is None or hist.empty:
        return result

    durations = hist["duration"].astype(float).values
    ts = hist["ts"]

    # --- stats ---
    ewma = ewma_ratio(durations)
    hawkes = hawkes_proxy(ts)
    iso_scores = isolation_forest_scores(durations)

    recent_iso = (
        float(np.mean(iso_scores[-3:]))
        if iso_scores is not None else 0.0
    )

    n_events = len(hist)
    conf_label = confidence_label(n_events)

    # ========================================================
    # SCORE DE SÉVÉRITÉ
    # ========================================================

    score = 0

    if anomaly.rule_anomaly:
        score += 2

    if ewma and ewma > 1.3:
        score += 2

    if hawkes and hawkes["rate_ratio"] > 1.5:
        score += 2

    if recent_iso > 0.7:
        score += 2

    if score >= 6:
        severity = "CRITICAL"
    elif score >= 4:
        severity = "MAJOR"
    elif score >= 2:
        severity = "WARNING"
    else:
        severity = "OK"

    result.update({
        "events_count": n_events,
        "window_days": int(hist["window_days"].iloc[0]),
        "confidence": conf_label,
        "ewma_ratio": ewma,
        "rate_ratio": hawkes["rate_ratio"] if hawkes else None,
        "burstiness": hawkes["burstiness"] if hawkes else None,
        "hawkes_score": score,
        "anomaly_score": round(recent_iso, 3),
        "severity": severity,
    })

    return result

