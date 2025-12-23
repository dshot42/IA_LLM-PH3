from typing import Dict, List, Optional
import torch
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import json
from threading import Thread
from transformers import TextIteratorStreamer
import os.path as op
import os
import sys
from ia.generate_repport import repportLLM
from config import Config

from supervision_handler.app.factory import socketio

llm_executor = ThreadPoolExecutor(max_workers=1)

def reduce_workflow(workflow: Dict, anomaly: Dict) -> Dict:
    """
    Réduction AUTOMATIQUE du workflow à partir de l'anomalie :
    - machine concernée
    - steps nominaux
    - durée et fenêtre nominales
    - codes erreur possibles
    """

    machine_id = anomaly["machine"]
    step_terminal = anomaly.get("step_name")

    # ==========================
    # INFOS LIGNE
    # ==========================
    light = {
        "ligne": workflow["ligne_industrielle"]["nom"],  
        "cycle_nominal_s": workflow["ligne_industrielle"]["cycle_nominal_s"],
        "machine": machine_id,
    }

    # ==========================
    # DURÉE & FENÊTRE NOMINALES
    # ==========================
    # Durée nominale machine
    light["duree_nominale_machine_s"] = (
        workflow["workflow_global"]["durees_nominales_s"]
        .get(machine_id)
    )

    # Fenêtre cycle nominal
    for seq in workflow["scenario_nominal"]["sequence"]:
        if seq["machine"] == machine_id:
            light["fenetre_cycle_nominale_s"] = f'{seq["start_at"]}-{seq["end_at"]}'
            break

    # ==========================
    # STEPS NOMINAUX MACHINE
    # ==========================
    steps = workflow["machines"][machine_id]["steps"]

    light["steps_nominal"] = [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"]
        }
        for s in steps
    ]

    # Index du step terminal dans la séquence nominale
    if step_terminal:
        step_ids = [s["id"] for s in steps]
        if step_terminal in step_ids:
            idx = step_ids.index(step_terminal)
            light["step_terminal_nominal_index"] = idx
            light["step_terminal_nominal"] = steps[idx]["name"]

            # Steps amont / aval (ultra utile pour le raisonnement LLM)
            light["steps_amont"] = [
                s["id"] for s in steps[:idx]
            ]
            light["steps_aval"] = [
                s["id"] for s in steps[idx + 1 :]
            ]

    # ==========================
    # CODES ERREUR POSSIBLES
    # ==========================
    light["error_codes_possibles"] = [
        {
            "code": e["code"],
            "error": e["error"],
            "description": e["cause"]
        }
        for e in workflow["machines"][machine_id].get("error_codes", [])
    ]

    # ==========================
    # DÉPENDANCES GRAFCET (AMONT / AVAL)
    # ==========================
    deps_amont = []
    deps_aval = []

    for t in workflow["grafcet"]["transitions"]:
        if t["to"].startswith("S") and t.get("condition"):
            if machine_id in t["condition"]:
                deps_amont.append(t["condition"])
        if t["from"].startswith("S") and t.get("condition"):
            if machine_id in t["condition"]:
                deps_aval.append(t["condition"])

    if deps_amont:
        light["dependances_amont"] = deps_amont
    if deps_aval:
        light["dependances_aval"] = deps_aval

    return light

def render_nominal_scenario(light: dict) -> str:
    lines = []

    lines.append(f"Machine nominale : {light['machine']}")
    lines.append(f"Durée nominale machine : {light.get('duree_nominale_machine_s', 'N/A')} s")
    lines.append(f"Fenêtre cycle nominale : {light.get('fenetre_cycle_nominale_s', 'N/A')}")

    lines.append("")
    lines.append("Enchaînement nominal des steps :")

    for i, s in enumerate(light.get("steps_nominal", []), start=1):
        lines.append(
            f"{i}. {s['id']} {s['name']} – {s['description']}"
        )

    if "step_terminal_nominal" in light:
        lines.append("")
        lines.append(
            f"Step terminal nominal attendu : "
            f"{light['steps_nominal'][light['step_terminal_nominal_index']]['id']} "
            f"{light['step_terminal_nominal']}"
        )

    if light.get("steps_amont"):
        lines.append("")
        lines.append(
            "Steps amont (doivent être exécutés avant) : "
            + ", ".join(light["steps_amont"])
        )

    if light.get("steps_aval"):
        lines.append(
            "Steps aval (doivent suivre) : "
            + ", ".join(light["steps_aval"])
        )

    if light.get("dependances_amont"):
        lines.append("")
        lines.append(
            "Dépendances Grafcet amont : "
            + " | ".join(light["dependances_amont"])
        )

    if light.get("dependances_aval"):
        lines.append(
            "Dépendances Grafcet aval : "
            + " | ".join(light["dependances_aval"])
        )

    if light.get("error_codes_possibles"):
        lines.append("")
        lines.append("Codes erreur possibles sur cette machine :")
        for e in light["error_codes_possibles"]:
            lines.append(
                f"- {e['code']} : {e['error']} ({e['description']})"
            )

    return "\n".join(lines)



def build_prompt_for_anomaly(workflow: str, anomaly: dict):
    """
    Prompt Mistral Instruct GGUF / HF
    Rapport industriel factuel, verbeux et démontrable
    """

    machine = anomaly.get("machine", "UNKNOWN")
    cycle = int(anomaly.get("cycle", 0))
    step = anomaly.get("step_name", "UNKNOWN")
    level = anomaly.get("level", "UNKNOWN")
    score = float(anomaly.get("anomaly_score", 0.0))
    severity = anomaly.get("severity", "UNKNOWN")

    n_errors = int(anomaly.get("n_step_errors", 0))

    cycle_duration = float(anomaly.get("cycle_duration_s", 0.0))
    duration_overrun = float(anomaly.get("duration_overrun_s", 0.0))

    ewma = anomaly.get("ewma_ratio")
    rate_ratio = anomaly.get("rate_ratio")
    burst = anomaly.get("burstiness")
    hawkes = anomaly.get("hawkes_score")

    rule_anomaly = anomaly.get("rule_anomaly", False)
    rule_reasons = anomaly.get("rule_reasons", [])

    workflow_light = reduce_workflow(
        workflow=json.loads(workflow),
        anomaly=anomaly
    )

    scenario_nominal_str = render_nominal_scenario(workflow_light)

    prompt = f"""
[INST]
RÔLE : Ingénieur process industrielle senior (PLC / Grafcet).

OBJECTIF :
Produire un rapport industriel détaillé analysant une anomalie de production
par comparaison STRICTE entre le scénario nominal officiel et les données réelles observées.

PRINCIPE FONDAMENTAL :
Le scénario nominal est la référence absolue.
Toute conclusion doit être fondée sur des écarts démontrables à partir des données fournies.

RÈGLES IMPÉRATIVES :
- Interdiction de causes inventées ou d’hypothèses non démontrées.
- Les données nominales et observées ne doivent pas être reformulées.
- Les constats et analyses doivent être formulés en phrases complètes.
- Toute information non démontrable doit être expliquée par l’insuffisance
  ou l’incohérence des données disponibles.
- Aucun markdown, aucun exemple générique.
- Longueur maximale du rapport : 1500 caractères.

SCÉNARIO NOMINAL OFFICIEL :
{scenario_nominal_str}

DONNÉES RÉELLES OBSERVÉES :
Machine = {machine}
Cycle = {cycle}
Step terminal observé = {step}
Niveau d’erreur PLC = {level}
Sévérité calculée = {severity}

Durée cycle machine mesurée = {cycle_duration:.2f} s
Dépassement de durée constaté = {duration_overrun:.2f} s

Règle(s) de détection déclenchée(s) = {rule_reasons}
Anomalie par règle = {rule_anomaly}

Score ML global = {score:.3f}
EWMA ratio = {ewma}
Rate ratio = {rate_ratio}
Burstiness = {burst}
Hawkes score = {hawkes}

Nombre d’erreurs PLC sur le cycle = {n_errors}

FORMAT STRICT DU RAPPORT :

Machine :
Step concerné :

Comportement nominal attendu :
Décrire le comportement attendu selon le scénario nominal officiel,
en particulier la durée cycle attendue et la fenêtre nominale.

Comportement réel observé :
Décrire factuellement le comportement observé à partir des données réelles,
notamment la durée cycle mesurée et le dépassement constaté.

Analyse NOMINAL vs RÉEL :
- Durée des steps :
- Durée cycle machine :
- Impact cycle global :
- Cohérence Grafcet :

Impact sur la production :
Décrire l’impact du dépassement de durée sur la performance de la ligne.

Causes techniques probables :
Uniquement des causes directement déductibles des données (ex : sur-temps global sans erreur PLC).

Actions terrain prioritaires :
Lister des actions concrètes de diagnostic ou de vérification terrain
cohérentes avec l’anomalie de durée constatée (maximum 5).

Niveau de criticité :
Qualifier la criticité (FAIBLE / MODÉRÉ / ÉLEVÉ / CRITIQUE)
en cohérence avec la sévérité et le dépassement temporel observé.

FIN_RAPPORT
[/INST]
""".strip()

    return prompt




def eval_prompt_anomaly_gguf(prompt: str, model, anomalie: dict):

    output = model.create_chat_completion(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.0,
        max_tokens=700,
        repeat_penalty=1.10,
        stop=["FIN_RAPPORT"]
    )

    # ✅ BON ACCÈS AU TEXTE
    result = output["choices"][0]["message"]["content"].strip()

    # 🔒 fallback intelligent
    if not result or len(result) < 50:
        result = (
            "Analyse non concluante en raison de données insuffisantes "
            "ou incohérentes pour caractériser un écart process mesurable. "
            "Un contrôle de la remontée des durées et des événements PLC est requis."
        )

    socketio.emit("anomalie", {"status": "completed"}, namespace="/")
    repportLLM(result, anomalie, prompt)

    return result





def eval_prompt_anomaly(prompt, model, tokenizer, anomalie):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=350,
            do_sample=False,           # 🔒 plus d'aléatoire
            temperature=0.0,           # 🔒
            repetition_penalty=1.05,
            no_repeat_ngram_size=4,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
        )

    decoded = tokenizer.decode(output[0], skip_special_tokens=True)

    # ✅ retire le prompt si le modèle l'a recopié
    if decoded.startswith(prompt):
        result = decoded[len(prompt):].strip()
    else:
        result = decoded.strip()

    socketio.emit("anomalie", {"status": "completed"}, namespace="/")
    repportLLM(result, anomalie, prompt)  # (tu avais oublié prompt dans repportLLM)
    return result



############## TRS ##############

def trs_prompt_diag(workflow, anomalies_df, trs: dict, period: dict, step_impact_pct=None) -> str:
    """
    Prompt TRS ultra-strict :
    - workflow nominal = référence absolue
    - aucune solution par défaut
    - aucun pourcentage inventé
    - analyse factuelle uniquement
    """

    # --- Sécurités ---
    if anomalies_df is None or anomalies_df.empty:
        anomalies_count = 0
        total_lost_time = 0.0
        anomalies_str = "Aucune anomalie détectée."
    else:
        anomalies_count = len(anomalies_df)

        if "duration_overrun_s" in anomalies_df.columns:
            total_lost_time = round(
                anomalies_df["duration_overrun_s"].clip(lower=0).sum(), 2
            )
        else:
            total_lost_time = "non mesurable"

        lines = []
        for _, row in anomalies_df.head(50).iterrows():
            lines.append(
                f"Cycle {int(row['cycle'])} | "
                f"Machine {row['machine']} | "
                f"StepId {row.get('step_id', 'UNKNOWN')} | "
                f"Step {row.get('step_name', 'UNKNOWN')} | "
                f"Level {row.get('level', 'UNKNOWN')} | "
                f"Overrun {round(row.get('duration_overrun_s', 0), 2)} s"
            )
        anomalies_str = "\n".join(lines)

    trs_value = trs.get("trs", trs)

    workflow_str = (
        workflow if isinstance(workflow, str)
        else json.dumps(workflow, ensure_ascii=False, indent=2)
    )

    # --- Bloc % factuels (optionnel) ---
    if step_impact_pct is None:
        impact_block = "Aucun pourcentage d'impact fourni."
        percent_rule = (
            "INTERDICTION ABSOLUE :\n"
            "- Tu ne dois produire AUCUN pourcentage, ratio ou statistique.\n"
            "- Tu dois uniquement qualifier les impacts à partir des overruns observés.\n"
        )
        output_format_line = "Machine | Step | Type d’écart | Impact cycle | Impact (qualitatif)"
    else:
        items = []
        iterable = list(step_impact_pct.items())
        iterable = sorted(iterable, key=lambda kv: float(kv[1]), reverse=True)[:10]

        for key, pct in iterable:
            if isinstance(key, tuple) and len(key) == 2:
                machine, step = key
            else:
                machine, step = "UNKNOWN", str(key)
            items.append(f"- {machine} | {step} | {float(pct):.1f}%")

        impact_block = "\n".join(items) if items else "Aucun pourcentage disponible."
        percent_rule = (
            "Les pourcentages ci-dessous sont CALCULÉS côté Python.\n"
            "INTERDICTION ABSOLUE :\n"
            "- Tu ne dois PAS recalculer.\n"
            "- Tu ne dois PAS extrapoler.\n"
            "- Tu dois réutiliser EXACTEMENT ces valeurs.\n"
        )
        output_format_line = "Machine | Step | Type d’écart | Impact cycle | Impact production % (fourni)"

    return f"""
Tu es un expert industriel senior (PLC / Grafcet / performance ligne).

Tu analyses une dérive TRS UNIQUEMENT à partir des données fournies.
Le WORKFLOW NOMINAL est la RÉFÉRENCE ABSOLUE.
Aucune interprétation non démontrée n’est autorisée.

RÈGLES ABSOLUES :
- Aucun méta-texte, aucune justification de méthode.
- Aucune invention (causes, pannes, maintenance, capteurs).
- Ne reformule pas les données brutes.
- Si une cause ou une action n’est pas démontrée : écrire STRICTEMENT "non démontré".

RÈGLES SUR LES % :
{percent_rule}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKFLOW NOMINAL (RÉFÉRENCE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{workflow_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Début : {period['start']}
Fin   : {period['end']}
TRS : {trs_value}
Anomalies : {anomalies_count}
Temps perdu vs nominal : {total_lost_time} s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANOMALIES OBSERVÉES (FACTUEL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{anomalies_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPACT PAR STEP (FACTUEL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{impact_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT STRICT DE SORTIE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1) Diagnostic TRS
- Commencer OBLIGATOIREMENT par : "TRS = {trs_value}"
- Phrase unique, factuelle, orientée workflow.

2) Erreurs par step (liste simple)
- {output_format_line}

3) Steps les plus impactants
- Machine | Step | Justification factuelle (overrun et/ou % fourni)

4) Analyse workflow
- 3 à 5 lignes maximum
- Uniquement constats démontrables (ordre, synchronisation, cycle global)

5) Actions
- Écrire "non démontré" si aucune action ne découle directement des données
""".strip()



def eval_prompt_trs(prompt, model, tokenizer, anomalie, period=None):

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    print(prompt)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=350,
            do_sample=False,        # 🔒 CRITIQUE
            temperature=0.0,        # 🔒 CRITIQUE
            repetition_penalty=1.05,
            no_repeat_ngram_size=4,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id
        )


    decoded = tokenizer.decode(output[0], skip_special_tokens=True)

    # 🔑 découpe robuste
    if decoded.startswith(prompt):
        result = decoded[len(prompt):].strip()
    else:
        result = decoded.strip()

    print("RESULT TRS LLM :\n", result)

    # 🔹 génération du PDF TRS
    repportLLM(
        result,
        anomalie,
        prompt
    )

    return result
