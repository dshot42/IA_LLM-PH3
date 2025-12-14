import psycopg2
import psycopg2.extras
import json
import time
import queue
import threading
import sys
from datetime import datetime
import config_plc
import os.path as op
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
# ============================================================
#  CONFIGURATION
# ============================================================

DB_CONFIG = config_plc.DB_CONFIG
EVENT_QUEUE = queue.Queue(maxsize=5000)

RECONNECT_DELAY = 3

# ============================================================
#  CONNEXION POSTGRES AVEC AUTO-RECONNECT
# ============================================================

def connect_db():
    while True:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.autocommit = True
            print("[DB] Connected to PostgreSQL.")
            return conn
        except Exception as e:
            print("[DB] Connection failed, retrying...", e)
            time.sleep(RECONNECT_DELAY)


# ============================================================
#  INSERTION D'UN EVENT
# ============================================================

SQL_INSERT = """
INSERT INTO plc_events (
    ts, machine, level, code, message,
    cycle, step_id, step_name, durection payload
) VALUES (
    %(ts)s, %(machine)s, %(level)s, %(code)s, %(message)s,
    %(cycle)s, %(step_id)s, %(step_name)s, %(duration)s, %(payload)s
);
"""

def format_event(evt):
    """Convertit l'event JSON brut en colonnes SQL compatibles avec plc_events."""
    return {
        "ts": evt["ts"],
        "machine": evt["machine"],
        "level": evt["level"],
        "code": evt.get("code"),
        "message": evt.get("message"),
        "cycle": evt.get("cycle"),
        "step_id": evt.get("step_id"),
        "step_name": evt.get("step_name"),
        "duration": evt.get("duration"),
        "payload": json.dumps(evt.get("payload", {}), ensure_ascii=False)
    }



# ============================================================
#  THREAD D'INGESTION PRINCIPAL
# ============================================================

class DBWriterThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.conn = connect_db()
        self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def run(self):
        print("[DBWriter] Started.")
        while True:
            evt = EVENT_QUEUE.get()
            if evt is None:
                break

            try:
                self.cursor.execute(SQL_INSERT, format_event(evt))
                print("INSERT EVENT SUCCESS ")
            except Exception as e:
                print("[DBWriter] Insert FAILED:", e)
                self.conn = connect_db()
                self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


# ============================================================
#  SIMULATEUR DE RECEPTION (à brancher sur ton simulateur)
# ============================================================

def process_incoming_event(evt_json):
    """
    Appelé pour chaque event venant du simulateur.
    evt_json = dict JSON complet.
    """
    try:
        EVENT_QUEUE.put(evt_json, timeout=1)
    except queue.Full:
        print("[WARN] EVENT_QUEUE full — event dropped.")
        

def tail_f(path):
    """Tail -f robuste pour un fichier JSONL."""
    
    # Attendre que le fichier existe avant d'essayer de l'ouvrir
    while not op.exists(path):
        print(f"[TAIL] Waiting for file to appear: {path}")
        time.sleep(0.5)

    print(f"[TAIL] Now watching: {path}")

    with open(path, "r", encoding="utf-8") as f:
        # Aller à la fin → ne lire que les nouvelles lignes
        f.seek(0, os.SEEK_END)

        buffer = ""

        while True:
            chunk = f.readline()

            if not chunk:
                time.sleep(0.05)
                continue

            # JSONL = une ligne = un JSON complet
            line = chunk.strip()

            if not line:
                continue

            yield line


def clean_db():
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.plc_events;")
        conn.commit()
    except Exception as e:
        print("Erreur lors du nettoyage de la table :", e)
        conn.rollback()
    finally:
        conn.close()
            
# ============================================================
#  DEMARRAGE
# ============================================================

if __name__ == "__main__":
    clean_db()
    writer = DBWriterThread()
    writer.start()

    print("[INFO] Ready to ingest events.")

    # Exemple : lecture en continu depuis stdin (simulateur pipeline)
    # Tu peux remplacer ici par un socket, websocket, pipe, fichier, etc.
    '''
    for line in sys.stdin:
        try:
            evt = json.loads(line.strip())
            process_incoming_event(evt)
        except Exception as e:
            print("[ERR] Invalid JSON :", e)
            '''
    log_file_path = "./ligne_PLC-advanced/log/events.jsonl"


    for line in tail_f(log_file_path):
        try:
            evt = json.loads(line)
            process_incoming_event(evt)
        except Exception as e:
            print("[ERR] Invalid JSON :", e, " line=", repr(line))

