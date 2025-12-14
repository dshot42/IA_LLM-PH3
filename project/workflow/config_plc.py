
# config.py
# Configuration du module d'analyse d'anomalies couplé à ton LLM

DB_CONFIG = {
    "dbname": "plc",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": 5432
}

# URL de ton LLM (ex : endpoint HTTP de ton serveur Phi-3 / Llama / autre)
LLM_ENDPOINT_URL = "http://localhost:8000/api/generate"

# Si ton LLM a besoin d'une clé API ou d'un token
LLM_API_KEY = None  # ou "ta_clef_ici"

# Fenêtre d'analyse : nombre de cycles récents à analyser
N_LAST_CYCLES = 200

# Score au-dessus duquel on considère qu'un point est anomal (IsolationForest)
ANOMALY_THRESHOLD = 1e-6  # plus petit => plus sensible
