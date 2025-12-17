
# detector.py
# Détection d'anomalies à partir des features (IsolationForest)

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import os.path as op
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config_plc  import ANOMALY_THRESHOLD

FEATURE_COLUMNS = [
    "n_events",
    "n_errors",
    "duration_s",
    "n_steps",
    "machine_order",
    "cycle_duration_s",
]


def train_isolation_forest(features: "pd.DataFrame") -> "IsolationForest":
    """Entraîne un IsolationForest sur les features sélectionnées."""
    X = features[FEATURE_COLUMNS].fillna(0).values
    model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=42,
    )
    model.fit(X)
    return model

def detect_anomalies(model: "IsolationForest", features: "pd.DataFrame") -> "pd.DataFrame":
    X = features[FEATURE_COLUMNS].fillna(0).values

    # Décision binaire interne du modèle
    #  1  = normal
    # -1  = anomalie
    y_pred = model.predict(X)

    # Score continu (plus grand = plus anormal)
    scores = -model.decision_function(X)

    features = features.copy()
    features["anomaly_score"] = scores
    features["is_anomaly"] = y_pred == -1

    return features


