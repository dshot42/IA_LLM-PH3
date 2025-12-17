from datetime import datetime, timezone
from sqlalchemy import text

import os
import sys
from supervision_handler.app.models import Part, PlcEvent
from supervision_handler.app.factory import db
import json


def insert_anomaly(pred):
    sql = text("""
        INSERT INTO plc_anomalies (
            cycle, machine, step_id, step_name,
            anomaly_score, rule_anomaly, rule_reasons,
            has_step_error, n_step_errors,
            cycle_duration_s, duration_overrun_s,
            events_count, window_days,
            ewma_ratio, rate_ratio, burstiness,
            hawkes_score, confidence,
            severity
        )
        VALUES (
            :cycle, :machine, :step_id, :step_name,
            :anomaly_score, :rule_anomaly, :rule_reasons,
            :has_step_error, :n_step_errors,
            :cycle_duration_s, :duration_overrun_s,
            :events_count, :window_days,
            :ewma_ratio, :rate_ratio, :burstiness,
            :hawkes_score, :confidence,
            :severity
        )
    """)

    payload = {
        **pred,
        "rule_reasons": json.dumps(pred.get("rule_reasons", []))
    }

    with db.engine.begin() as conn:
        conn.execute(sql, payload)
