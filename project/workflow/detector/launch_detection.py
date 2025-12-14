
# run_detection.py
# Script principal : extraction features -> détection anomalies -> explication LLM

from datetime import datetime, timedelta, timezone
import torch
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from feature_handler import fetch_events_df, build_cycle_features,add_duration_overrun, add_nominal_deviation, rule_based_anomalies
from detector import train_isolation_forest, detect_anomalies
from prompt_handler import build_prompt_for_anomaly,eval_prompt_anomaly, eval_prompt_trs, trs_prompt_diag
import os.path as op
import os
import sys
import TRS_handler

from supervision_handler.app.factory import socketio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import generate_repport

from config import Config
import model as model_utils

workflow_file = os.path.join(Config.folder_workflow,  "workflow.json")
with open(workflow_file, "r", encoding="utf-8") as f:
    workflow_content = f.read()

tokenizer = model_utils.load_tokenizer()
#model = model_utils.load_model_with_qlora()       
model = model_utils.load_standard_model()  


def check_anomalies(param):
    print("[INFO] Chargement des événements depuis PostgreSQL...")
    df_events = fetch_events_df(param)
    if df_events.empty:
        print("[WARN] Aucun événement trouvé dans la base.")
        return

    print(f"[INFO] {len(df_events)} événements récupérés.")
    features = build_cycle_features(df_events)
    features = add_nominal_deviation(features, workflow_content)
    features = add_duration_overrun(features, workflow_content)
    features = rule_based_anomalies(features, workflow_content)

    ml_candidates = features[features["rule_anomaly"]]

    model = train_isolation_forest(ml_candidates)
    features_scored = detect_anomalies(model, ml_candidates)

    anomalies = features_scored[features_scored["is_anomaly"]].sort_values(
        "anomaly_score", ascending=False
    )

    if anomalies.empty:
        print("[INFO] Aucune anomalie significative détectée.")
        return

    
    if (param["LLM_RESULT"] == False):
        return anomalies
    
    print(f"[INFO] {len(anomalies)} anomalies détectées, envoi vers LLM pour analyse...")

    for _, row in anomalies.iterrows():
        prompt = build_prompt_for_anomaly(workflow_content, row, workflow_content)
        print("\n================= ANOMALIE =================")
        print(f"Machine: {row['machine']}, cycle: {int(row['cycle'])}, score: {row['anomaly_score']:.3f}")
        print("--------------------------------------------")
        
        socketio.emit(
            "anomaly_result",
            {"result": row}
        )
        
        llm_answer = eval_prompt_anomaly(prompt=prompt,model= model,tokenizer= tokenizer,row = row)
        print("RESULT " , llm_answer)
            
        print("============================================\n")
        

               
def get_TRS_and_diagnostic_anomaly_impact(param):
    # on get TRS sur la periode (end-start)
    # on get les rapport selon la periode souhaité
    # on envoie au LLM avec prompt d'analyse d'impact sur le TRS 
    #analyse perte de rendement , analyse des plus gros impact
    # point d'amelioration
    anomalies_df = check_anomalies(param)

    trs = TRS_handler.calculate_trs(
        workflow_content,
        param["start"],
        param["end"]
    )

    period = {
        "start": param["start"].isoformat(),
        "end": param["end"].isoformat()
    }

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
