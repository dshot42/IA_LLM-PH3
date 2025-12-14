
Module d'analyse d'anomalies industrielles couplé à un LLM
=========================================================

Fichiers:
- config.py            : configuration DB + LLM + seuils
- feature_builder.py   : extraction events PostgreSQL -> features time-series
- detector.py          : IsolationForest pour détection anomalies
- llm_interface.py     : construction prompt + appel HTTP vers ton LLM
- run_detection.py     : script principal (pipeline complet)

Dépendances Python (exemple):
    pip install psycopg2-binary pandas scikit-learn requests

Usage:
1) Vérifie config.py (DB_CONFIG, LLM_ENDPOINT_URL, etc.)
2) Assure-toi que la table plc_events est alimentée (via ton simulateur + pipeline ingest).
3) Lance:
    python run_detection.py

Le script va:
- récupérer les derniers cycles,
- calculer des features par cycle/machine,
- entraîner IsolationForest,
- détecter les anomalies,
- envoyer les anomalies au LLM pour obtenir une analyse textuelle détaillée.
