
# run_detection.py
# Script principal : extraction features -> détection anomalies -> explication LLM

from datetime import datetime, timedelta, timezone
import torch
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from workflow.detector.feature_handler import (
    emit_anomalies_df,
    project_step_to_cycle,
    build_step_features,
    fetch_events_df,
    build_cycle_features,
    add_duration_overrun,
    add_nominal_deviation,
    rule_based_anomalies,
)
from workflow.detector.detector import train_isolation_forest, detect_anomalies
from workflow.detector.prompt_handler import build_prompt_for_anomaly,eval_prompt_anomaly, eval_prompt_trs, trs_prompt_diag
import os.path as op
import os
import sys
from workflow.detector.TRS_handler import calculate_trs
import pandas as pd
import psycopg2
from supervision_handler.app.factory import socketio,db
from workflow.detector.predicat_handler import compute_prediction
from supervision_handler.app.service.anomalie_service import insert_anomaly

from config import Config
import ia.model as model_utils

workflow_file = os.path.join(Config.folder_workflow,  "workflow.json")
with open(workflow_file, "r", encoding="utf-8") as f:
    workflow_content = f.read()

tokenizer = model_utils.load_tokenizer()
#model = model_utils.load_model_with_qlora()       
model = model_utils.load_standard_model()  

from config_plc import DB_CONFIG

# ============================================================
# DB
# ============================================================


def check_anomalies(df_events, param):
    print("[INFO] Chargement des événements depuis PostgreSQL...")

    if df_events.empty:
        print("[WARN] Aucun événement trouvé.")
        return None

    print(f"[INFO] {len(df_events)} événements récupérés.")

    # ==================================================
    # 1️⃣ FEATURES STEP (preuves terrain)
    # ==================================================
    step_df = build_step_features(df_events)
    step_cycle_features = project_step_to_cycle(step_df)

    # ==================================================
    # 2️⃣ FEATURES CYCLE (base ML)
    # ==================================================
    features = build_cycle_features(df_events)

    features = features.merge(
        step_cycle_features,
        on=["cycle", "machine"],
        how="left"
    )

    # sécurité colonnes
    if "faulty_step_id" in features.columns:
        features["step_id"] = features["faulty_step_id"].fillna(features["step_id"])

    features["has_step_error"] = features["has_step_error"].fillna(False)
    features[["n_step_errors", "max_step_duration", "sum_step_duration"]] = (
        features[["n_step_errors", "max_step_duration", "sum_step_duration"]]
        .fillna(0)
    )

    # ==================================================
    # 3️⃣ COMPARAISON NOMINALE + RÈGLES
    # ==================================================
    features = add_nominal_deviation(features, workflow_content)
    features = add_duration_overrun(features, workflow_content)
    features = rule_based_anomalies(features, workflow_content)

    # Une erreur STEP rend le cycle suspect
    features["rule_anomaly"] |= features["has_step_error"]

    # ==================================================
    # 4️⃣ DÉTECTION ML (score, pas décision)
    # ==================================================
    candidates = features[features["rule_anomaly"]]

    if candidates.empty:
        print("[INFO] Aucune erreur détectée.")
        return None

    model = train_isolation_forest(candidates)
    scored = detect_anomalies(model, candidates)

    # 🔑 le score DOIT TOUJOURS exister
    features["anomaly_score"] = 0.0
    features["is_anomaly"] = False

    features.loc[scored.index, "anomaly_score"] = scored["anomaly_score"]
    features.loc[scored.index, "is_anomaly"] = scored["is_anomaly"]

    anomalies = features[features["rule_anomaly"]].copy()

    print("---- RULE STATS ----")
    print(anomalies[["rule_anomaly", "has_step_error"]].value_counts())

    # ==================================================
    # 🔮 5️⃣ PRÉDICTION (historique)
    # ==================================================
    predictions = []

    for _, row in anomalies.iterrows():
        pred = compute_prediction(row)

        if pred is not None:
            pred.update({
                "cycle": int(row["cycle"]),
                "machine": row["machine"],
                "step_id": row["step_id"],
                "code": row.get("code"),
            })
            predictions.append(pred)

    if predictions:
        pred_df = pd.DataFrame(predictions)

        anomalies = anomalies.merge(
            pred_df,
            on=["cycle", "machine", "step_id", "code"],
            how="left"
        )
        anomalies["severity"] = (
            anomalies["severity_y"]
            .fillna(anomalies["severity_x"])
        )

        # nettoyage
        anomalies.drop(columns=["severity_x", "severity_y"], inplace=True)

    # ==================================================
    # 6️⃣ INSERT DB (APRÈS enrichissement)
    # ==================================================
    for _, row in anomalies.iterrows():
        insert_anomaly(row.to_dict())

    # ==================================================
    # 7️⃣ EMIT FRONT
    # ==================================================
    emit_anomalies_df(anomalies)

    # ==================================================
    # 8️⃣ LLM (optionnel)
    # ==================================================
    if param.get("LLM_RESULT") is True:
        llm_anomalie_analyse(anomalies)

    return anomalies


    
    
from datetime import datetime, timezone

def llm_anomalie_analyse(conn, anomalies):

    print(f"[INFO] {len(anomalies)} anomalies détectées, analyse LLM en cours...")

    for _, row in anomalies.iterrows():

        # 1️⃣ Calcul prédiction (EWMA + Proxy Hawkes)
        prediction = compute_prediction( row)

        verdict ="todo"
        # 2️⃣ Prompt LLM (FACTS ONLY)
        prompt = build_prompt_for_anomaly(
            workflow_content,
            row,
            workflow_content,
            prediction={
                **prediction,
                "verdict": verdict
            } if prediction else None
        )

        print("\n================= ANOMALIE =================")
        print(
            f"Machine: {row['machine']} | "
            f"Step: {row['step_id']} | "
            f"Cycle: {int(row['cycle'])} | "
            f"Score: {row['anomaly_score']:.3f} | "
            f"Verdict: {verdict}"
        )

        if prediction:
            print(
                f"Prediction → "
                f"ewma={prediction['ewma_ratio']} | "
                f"rate_ratio={prediction['rate_ratio']} | "
                f"burst={prediction['burstiness']} | "
                f"conf={prediction['confidence']} | "
                f"window={prediction['window_days']}d"
            )

        # 3️⃣ Emit front
        socketio.emit(
            "anomaly_LLM",
            {
                "anomaly": row.to_dict(),
                "prediction": prediction,
                "verdict": verdict
            }
        )

        # 4️⃣ Appel LLM
        llm_answer = eval_prompt_anomaly(
            prompt=prompt,
            model=model,
            tokenizer=tokenizer,
            row=row
        )

        print("RESULT", llm_answer)
        print("============================================\n")

    return anomalies



               
def get_TRS_and_diagnostic_anomaly_impact(param):
    # on get TRS sur la periode (end-start)
    # on get les rapport selon la periode souhaité
    # on envoie au LLM avec prompt d'analyse d'impact sur le TRS 
    #analyse perte de rendement , analyse des plus gros impact
    # point d'amelioration
    df_events = fetch_events_df(param)
    anomalies_df = check_anomalies(df_events,param)

    trs = calculate_trs(
        db,
        workflow_content,
        param["start"],
        param["end"]
    )

    period = {
        "start": param["start"].isoformat(),
        "end": param["end"].isoformat()
    }

    # predicate
    prompt = trs_prompt_diag(workflow_content, anomalies_df, trs, period)
    eval_prompt_trs(prompt=prompt,model= model,tokenizer= tokenizer,anomalies_df = anomalies_df)
    

if __name__ == "__main__":

    param = {
        "only_last": False,
        "start":  datetime.now(timezone.utc) - timedelta(days=2),
        "end": datetime.now(timezone.utc),
        "part_id": "",
        "ligne": "",
        "LLM_RESULT" : True
    }
    #check_anomalies(param) 
    
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
    get_TRS_and_diagnostic_anomaly_impact(param2)
    
    
    
