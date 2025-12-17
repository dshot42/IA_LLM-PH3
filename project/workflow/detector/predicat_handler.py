import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from supervision_handler.app.factory import db


SEVERITY_ORDER = {
    "OK": 0,
    "NO_HISTORY": 1,      # anomalie détectée mais pas assez d'historique pour estimer l'impact
    "CYCLE_DRIFT": 2,
    "STEP_ERROR": 3,
    "WARNING": 4,
    "MAJOR": 5,
    "CRITICAL": 6,
}

CONFIDENCE_MAP = {
    "insufficient": 0.0,
    "low": 0.3,
    "medium": 0.6,
    "high": 1.0,
}

# -------------------------
# CONFIDENCE
# -------------------------
def confidence_level(n):
    if n >= 30:
        return "high"
    if n >= 20:
        return "medium"
    if n >= 10:
        return "low"
    return "insufficient"


# -------------------------
# EWMA (amplification)
# -------------------------
def ewma_ratio(values, alpha=0.3):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]

    if len(values) < 1:
        return None

    e = np.median(values[:3])  # plus robuste
    start = e

    for v in values:
        e = alpha * v + (1 - alpha) * e

    return round(e / max(start, 1e-9), 2)



# -------------------------
# PROXY HAWKES
# -------------------------
def hawkes_proxy(ts):
    ts = pd.to_datetime(ts, utc=True).sort_values()
    if len(ts) < 1:
        return None

    inter = np.diff(ts.values.astype("datetime64[s]").astype(np.int64))
    if len(inter) == 0:
        return None

    mu, sigma = np.mean(inter), np.std(inter)
    burst = (sigma - mu) / (sigma + mu) if mu + sigma > 0 else 0.0

    t0, tN = ts.iloc[0], ts.iloc[-1]
    total_rate = len(ts) / max((tN - t0).total_seconds(), 1)

    cutoff = ts.iloc[int(len(ts) * 0.7)]
    recent_rate = len(ts[ts >= cutoff]) / max((tN - cutoff).total_seconds(), 1)

    return {
        "rate_ratio": round(recent_rate / total_rate, 2),
        "burstiness": round(burst, 2),
    }


def hawkes_score(proxy):
    score = 0
    if proxy["rate_ratio"] > 1.5:
        score += 2
    if proxy["rate_ratio"] > 2.0:
        score += 2
    if proxy["burstiness"] > 0.3:
        score += 2
    if proxy["burstiness"] > 0.5:
        score += 2
    return score


def compute_severity(
    hawkes_score: float,
    ewma_ratio: float,
    confidence: float,
    rule_severity: str = "OK",
    has_step_error: bool = False,
    cycle_overrun_s: float = 0.0,
) -> str:
    """
    Sévérité finale = max(rule severity, predictive severity)
    - rule_severity: sortie de rule_based_anomalies (STEP_ERROR / CYCLE_DRIFT / OK / ...)
    - has_step_error: si vrai -> priorité haute
    - cycle_overrun_s: dépassement de cycle (secondes)
    """

    # --------- sécurité types ---------
    hawkes_score = float(hawkes_score or 0.0)
    ewma_ratio = float(ewma_ratio or 0.0)
    confidence = float(confidence or 0.0)
    cycle_overrun_s = float(cycle_overrun_s or 0.0)

    # --------- 1) sévérité "terrain" (règles) ---------
    base = rule_severity or "OK"

    # hard override: une erreur step = critique terrain
    if has_step_error:
        base = "STEP_ERROR"

    # --------- 2) sévérité "prédictive" ---------
    # Si pas de confiance ou pas d'historique : on ne sur-alarme pas
    if confidence < 0.2:
        pred = "NO_HISTORY"
    else:
        # Exemple de seuils simples
        # ewma_ratio > 1.0 signifie aggravation vs baseline (selon ta définition)
        score = 0

        # Hawkes : intensité de répétition
        if hawkes_score >= 3.0:
            score += 3
        elif hawkes_score >= 1.5:
            score += 2
        elif hawkes_score >= 0.8:
            score += 1

        # EWMA : dérive / amplification
        if ewma_ratio >= 2.0:
            score += 3
        elif ewma_ratio >= 1.3:
            score += 2
        elif ewma_ratio >= 1.1:
            score += 1

        # Dépassement cycle : impact immédiat
        if cycle_overrun_s >= 30:
            score += 2
        elif cycle_overrun_s >= 10:
            score += 1

        # Mapping score → label
        if score >= 6:
            pred = "CRITICAL"
        elif score >= 4:
            pred = "MAJOR"
        elif score >= 2:
            pred = "WARNING"
        else:
            pred = "OK"

    # --------- 3) fusion : max(base, pred) ---------
    base_rank = SEVERITY_ORDER.get(base, 0)
    pred_rank = SEVERITY_ORDER.get(pred, 0)

    final_sev = base if base_rank >= pred_rank else pred
    return final_sev




# -------------------------
# SQL STACK
# -------------------------
def fetch_similar_events( machine, step_id, code, since_ts):
    sql = """
    SELECT ts, duration
    FROM plc_events
    WHERE machine = %s
      AND step_id = %s
      AND code = %s
      AND level IN ('ERROR','FAULT','ALARM')
      AND ts >= %s
    ORDER BY ts ASC;
    """
    return pd.read_sql(sql, db.engine, params=(machine, step_id, code, since_ts) )


def fetch_similar_events_adaptive(
     machine, step_id, code,
    min_events=10, min_days=3, max_days=30, step_days=2
):
    now = datetime.now(timezone.utc)
    days = min_days

    while days <= max_days:
        since = now - timedelta(days=days)
        df = fetch_similar_events( machine, step_id, code, since)
        if len(df) >= min_events:
            df["window_days"] = days
            return df
        days += step_days

    df["window_days"] = max_days
    return df



# -------------------------
# PREDICTION FINALE
# -------------------------
def compute_prediction( row):
    # CONTRAT STRICT : toujours retourner ces clés
    result = {
        "events_count": 0,
        "window_days": 0,
        "confidence": 0.0,
        "ewma_ratio": 0.0,
        "rate_ratio": 0.0,
        "burstiness": 0.0,
        "hawkes_score": 0.0,
        "severity": "NO_HISTORY",
    }

    df = fetch_similar_events_adaptive(
        row["machine"],
        row["step_id"],
        row.get("code")
    )

    # ⚠️ CAS NORMAL EN TEMPS RÉEL
    if df is None or len(df) < 1:
        return result   # ✅ schéma respecté

    ewma = ewma_ratio(df["duration"].values)
    proxy = hawkes_proxy(df["ts"])
    h_score = hawkes_score(proxy) if proxy else 0
    conf_label = confidence_level(len(df))
    conf_score= CONFIDENCE_MAP[conf_label]

    severity = compute_severity(
        hawkes_score=h_score,
        ewma_ratio=ewma,
        confidence=conf_score,
        rule_severity=row.get("severity", "OK"),
        has_step_error=row.get("has_step_error", False),
        cycle_overrun_s=row.get("duration_overrun_s", 0.0),
    )


    result.update({
        "events_count": int(len(df)),
        "window_days": int(df["window_days"].iloc[0]),
        "confidence": conf_score, 
        "confidence_label": conf_label, 
        "ewma_ratio": ewma,
        "rate_ratio": proxy["rate_ratio"] if proxy else 0.0,
        "burstiness": proxy["burstiness"] if proxy else 0.0,
        "hawkes_score": h_score,
        "severity": severity,
    })

    return result