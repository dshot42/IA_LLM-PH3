from datetime import datetime, timezone
from sqlalchemy import text

import os
import sys
from supervision_handler.app.models import Part, PlcEvent
from supervision_handler.app.factory import db
import json
import numpy as np

def normalize_anomaly_inplace(a: dict):
    if isinstance(a.get("rule_reasons"), (list, dict)):
        a["rule_reasons"] = json.dumps(a["rule_reasons"])

    for k, v in a.items():
        if isinstance(v, np.generic):
            a[k] = float(v)
            
def update_anomaly(anomalie: dict):
    """
    Met à jour une anomalie EXISTANTE avec des données prédictives.
    Ne touche jamais aux champs terrain.
    """

    if "id" not in anomalie:
        raise ValueError("update_anomaly nécessite anomalie['id']")

    sql = text("""
        UPDATE plc_anomalies
        SET
            anomaly_score      = :anomaly_score,
            events_count       = :events_count,
            window_days        = :window_days,
            ewma_ratio         = :ewma_ratio,
            rate_ratio         = :rate_ratio,
            burstiness         = :burstiness,
            hawkes_score       = :hawkes_score,
            confidence         = :confidence,
            severity           = :severity
        WHERE id = :id
    """)

    normalize_anomaly_inplace(anomalie)
    
    payload = {
        "id": anomalie["id"],

        "anomaly_score": anomalie.get("anomaly_score"),
        "events_count": anomalie.get("events_count"),
        "window_days": anomalie.get("window_days"),

        "ewma_ratio": anomalie.get("ewma_ratio"),
        "rate_ratio": anomalie.get("rate_ratio"),
        "burstiness": anomalie.get("burstiness"),

        "hawkes_score": anomalie.get("hawkes_score"),
        "confidence": anomalie.get("confidence"),
        "severity": anomalie.get("severity"),
    }

    with db.engine.begin() as conn:
        conn.execute(sql, payload)
