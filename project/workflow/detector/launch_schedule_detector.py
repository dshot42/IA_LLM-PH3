import threading
import time
from datetime import datetime, timedelta, timezone
import launch_detection

def seconds_until_next_run(hour: int, minute: int, tz=timezone.utc):
    now = datetime.now(tz)

    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if next_run <= now:
        next_run += timedelta(days=1)

    return (next_run - now).total_seconds()


def check_detector(last_detection):
    print("▶ Reprise depuis :", last_detection)

    while True:
        start_loop = datetime.now(timezone.utc)
        now = start_loop

        param = {
            "only_last": False,
            "start": last_detection,
            "end": now,
            "part_id": "",
            "ligne": "",
            "LLM_RESULT": True
        }

        try:
            launch_detection.check_anomalies(param)
            last_detection = now
        except Exception as e:
            print("Erreur check_detector:", e)

        # sleep jusqu'à la prochaine minute
        elapsed = (datetime.now(timezone.utc) - start_loop).total_seconds()
        sleep_s = max(0, 5 - elapsed)
        time.sleep(sleep_s)


def daily_anomaly_job():
    
    print(f"[{datetime.utcnow()}] Diagnostic du jour lancée")

    param2 = {
        "line" : "",
        "start":  datetime.now(timezone.utc) - timedelta(days=2),
        "end": datetime.now(timezone.utc),
        "period" : "day", #hour day week month year 
        "LLM_RESULT" : False
        # on fait un rapport par jour basé sur tous les rapports de la journée ,
        # un rapport par semaine basé sur les rapports des jour,
        # un rapport par mois basé sur les rapport des semaine
        # un rapport par an par rapport des mois !!! 
    }
    # generer une short synthese a chaque fois pour analyse 
    launch_detection.get_TRS_and_diagnostic_anomaly_impact(param2)

    print("Détection terminée")


def dayly_report_scheduler(hour: int, minute: int):
    while True:
        sleep_seconds = seconds_until_next_run(hour, minute)
        print(f"Prochaine exécution dans {sleep_seconds/3600:.2f}h")
        time.sleep(sleep_seconds)

        try:
            daily_anomaly_job()
        except Exception as e:
            # ⚠️ jamais laisser mourir le thread
            print("Erreur détection proactive:", e)


def start_scheduler():
    dayly_report = threading.Thread(
        target=dayly_report_scheduler,
        args=(0, 0),   # ⏰ 00:00 UTC
        daemon=True
    )
    dayly_report.start()
    
    last_detection = datetime.now(timezone.utc)
    
    t = threading.Thread(
        target=check_detector,
        args=(last_detection,),
        daemon=True
    )
    t.start()



if __name__ == "__main__":
    start_scheduler()
    print("🟢 Scheduler démarré, process maintenu vivant")

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("⛔ Arrêt demandé")