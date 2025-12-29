
# run_detection.py
# Script principal : extraction features -> détection anomalies -> explication LLM

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from supervision_handler.app.models import PlcAnomaly,model_to_dict
from workflow.detector.detector import detector_anomalies, get_last_event
from workflow.detector.prompt_handler import build_prompt_for_anomaly,eval_prompt_anomaly_gguf, eval_prompt_trs, trs_prompt_diag
import os.path as op
import os
import sys
from workflow.detector.TRS_handler import calculate_trs
import pandas as pd
import psycopg2
from supervision_handler.app.factory import socketio,db
from workflow.detector.predicat_handler import compute_prediction
from supervision_handler.app.service.anomalie_service import update_anomaly
from supervision_handler.app.extensions import tokenizer, model
from config import Config
import ia.model as model_utils
from workflow.detector.feature_handler import fetch_events_df
import json 
from sqlalchemy.inspection import inspect

workflow_file = os.path.join(Config.folder_workflow,  "workflow.json")
with open(workflow_file, "r", encoding="utf-8") as f:
    workflow_content = f.read()

import numpy as np
import math

def py_scalar(x):
    # None stays None
    if x is None:
        return None

    # numpy scalars -> python scalars
    if isinstance(x, (np.generic,)):
        x = x.item()

    # NaN/inf -> None (Postgres n'aime pas toujours)
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None

    return x

def json_safe(val):
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    return val

# ============================================================
# CHECK ANOMALIE ON CYCLE 
# ============================================================

def check_anomalies(param):
    workflow = json.loads(workflow_content)
    anomalie = detector_anomalies( get_last_event(param.get("part_id")), workflow)
    if anomalie is None : 
        print("Aucune anomalie Détecté ")
        return 
    

    print("Anomalie Détecté  ! ")
    # 5. prédiction
    
    print("------------ ANOMALIE ------------")
    #print(anomalie.toDict())

    prediction = compute_prediction(anomalie)
    print("------------ PREDICTION ------------")
    #print(prediction)
    
    """
    for k, v in prediction.items():
        if hasattr(anomalie, k):
            setattr(anomalie, k, py_scalar(v))

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    raise
    """
    # 8. LLM
    if param.get("LLM_RESULT") is True and anomalie.id is not None:
        llm_anomalie_analyse(anomalie)

    return anomalie

########################################################

from datetime import datetime, timezone

def llm_anomalie_analyse(anomalie_obj:PlcAnomaly):
    """
    Analyse LLM d'une anomalie PLC déjà détectée et enrichie.
    - event    : dernier plc_event brut (contexte)
    - anomalie : dict issu de plc_anomalies (terrain + prédictif)
    """

    anomalie = model_to_dict(anomalie_obj)
    print("[INFO] Analyse LLM anomalie en cours...")

    # --------------------------------------------------
    # 1️⃣ Verdict initial (LLM décidera, pas nous)
    # --------------------------------------------------
    verdict = "UNASSESSED"

    # --------------------------------------------------
    # 2️⃣ Construction du prompt (FACTS ONLY)
    # --------------------------------------------------
    prompt = build_prompt_for_anomaly(
        workflow=workflow_content,
        anomaly={
            **anomalie,
            "verdict": verdict
        }
    )

    # --------------------------------------------------
    #  Logs console (debug lisible)
    # --------------------------------------------------


    # --------------------------------------------------
    # 5️⃣ Appel LLM
    # --------------------------------------------------
    llm_answer = eval_prompt_anomaly_gguf(
        "",
        prompt,
        model=model,
        anomalie=anomalie
    )

    print("\n=========== RÉSULTAT LLM ===========")
    print(llm_answer)
    print("===================================\n")

    return {
        **anomalie,
        "llm_analysis": llm_answer,
        "llm_verdict": verdict
    }
               
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
    
    
    
