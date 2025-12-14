import torch
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from threading import Thread
from transformers import TextIteratorStreamer
import os.path as op
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import generate_repport
from config import Config

from supervision_handler.app.factory import socketio

llm_executor = ThreadPoolExecutor(max_workers=1)



def anomalies_df_to_text(anomalies_df):
    if anomalies_df is None or anomalies_df.empty:
        return "Aucune anomalie significative détectée."

    lines = []
    for _, r in anomalies_df.iterrows():
        lines.append(
            f"Cycle {int(r['cycle'])} | "
            f"Machine {r['machine']} | "
            f"Durée réelle {r['cycle_duration_s']:.1f}s | "
            f"Surplus {r['duration_overrun_s']:.1f}s | "
            f"Score {r.get('anomaly_score', 0):.3f}"
        )
    return "\n".join(lines)



def build_prompt_for_anomaly(workflow, anomaly_row, context):
    """
    Prompt expert industriel :
    - workflow nominal = référence absolue
    - analyse causale NOMINAL vs RÉEL
    - focalisation sur step terminal + impact cycle
    """

    machine = anomaly_row["machine"]
    cycle = int(anomaly_row["cycle"])
    step = anomaly_row.get("step_name", "UNKNOWN")
    level = anomaly_row.get("level", "UNKNOWN")
    score = float(anomaly_row["anomaly_score"])
    n_errors = int(anomaly_row["n_errors"])
    duration_machine = float(anomaly_row["duration_s"])
    cycle_duration = float(anomaly_row["cycle_duration_s"])
    n_events = int(anomaly_row["n_events"])

    workflow_str = (
        workflow if isinstance(workflow, str)
        else json.dumps(workflow, ensure_ascii=False, indent=2)
    )

    prompt = f"""
Tu es une IA experte en supervision industrielle et en analyse de workflows automatisés
(PLC, Grafcet, CNC, robotique, synchronisation multi-machines).

Tu interviens comme un ingénieur process / méthodes senior chargé d’expliquer
UNE ANOMALIE DE PRODUCTION en comparant STRICTEMENT le comportement RÉEL
au WORKFLOW NOMINAL OFFICIEL (référence absolue).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKFLOW NOMINAL OFFICIEL (RÉFÉRENCE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Le workflow ci-dessous définit le comportement NORMAL attendu de la ligne :
- ordre et synchronisation des machines
- enchaînement des steps (Grafcet machine)
- durées nominales par machine et par cycle
- logique nominale du cycle global

Toute divergence doit être interprétée comme une dérive de process.

WORKFLOW NOMINAL :
{workflow_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANOMALIE OBSERVÉE (DONNÉES RÉELLES)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cette anomalie a été détectée automatiquement par analyse statistique
(IsolationForest) à partir des logs PLC réels.

- Machine concernée : {machine}
- Cycle de production : {cycle}
- Step terminal observé : {step}
- Niveau d’erreur final : {level}
- Sévérité statistique (ML score) : {score:.3f}
- Nombre d’événements PLC : {n_events}
- Nombre d’erreurs PLC : {n_errors}
- Durée réelle machine (cycle machine agrégé) : {duration_machine:.2f} s
- Durée réelle du cycle global : {cycle_duration:.2f} s

IMPORTANT :
Le "Step terminal observé" correspond au DERNIER step exécuté sur cette machine
pour ce cycle. Il représente généralement le point de blocage, de dérive
ou de ralentissement effectif du workflow.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OBJECTIF DE L’ANALYSE (OBLIGATOIRE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tu dois analyser cette anomalie en COMPARANT EXPLICITEMENT :

RÉEL  ⟷  NOMINAL (workflow officiel)

L’analyse doit impérativement répondre aux points suivants :

1) Quel est le RÔLE du step "{step}" dans le workflow nominal ?
   (fonction, position dans le Grafcet, dépendances amont / aval)

2) Quel comportement NOMINAL est attendu à ce step ?
   - durée nominale attendue
   - conditions de sortie normales
   - synchronisation attendue avec les autres machines

3) En quoi le comportement RÉEL s’en écarte-t-il ?
   - sur-durée / blocage / erreur / désynchronisation
   - impact sur la durée machine et le cycle global

4) Analyse NOMINAL vs RÉEL :
   • cohérence durée step (via durée machine agrégée)
   • cohérence durée cycle machine
   • impact sur le cycle global
   • respect ou violation de la logique Grafcet

5) Quel est l IMPACT INDUSTRIEL réel ?
   - allongement cycle
   - déphasage inter-machines
   - accumulation buffers
   - baisse de TRS (conformité workflow)

6) Quelles sont les CAUSES TECHNIQUES PROBABLES,
   uniquement si elles sont compatibles avec :
   - le step concerné
   - le niveau d’erreur observé
   - le type de dérive temporelle

7) Quelles ACTIONS TERRAIN immédiates
   un technicien / automaticien doit réaliser ?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTRAINTES ABSOLUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Ne JAMAIS reformuler ou répéter les données brutes.
- Ne JAMAIS inventer de causes non observables.
- Toujours raisonner à partir du workflow nominal.
- Rester factuel, exploitable terrain, orienté process.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT STRICT DE LA RÉPONSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- **Machine :**
- **Step concerné :**
  (nom exact + rôle nominal dans le workflow)
- **Comportement nominal attendu :**
- **Comportement réel observé :**
- **Analyse NOMINAL vs RÉEL :**
  • durée step  
  • durée cycle machine  
  • impact cycle global  
  • cohérence Grafcet  
- **Impact sur la production :**
- **Causes techniques probables :**
- **Actions de diagnostic terrain prioritaires :**
- **Niveau de criticité :**
  FAIBLE / MODÉRÉ / ÉLEVÉ / CRITIQUE
""".strip()

    return prompt


def eval_prompt_anomaly(prompt, model, tokenizer, row):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True
    )


    def run():
        with torch.no_grad():
            model.generate(
                **inputs,
                max_new_tokens=500,
                do_sample=True,
                temperature=0.3,
                top_p=0.9,
                repetition_penalty=1.08,
                no_repeat_ngram_size=3
            )

    Thread(target=run, daemon=True).start()

    # 🔥 streaming token par token
    full_text = ""
    for token in streamer:
        print(full_text)
        full_text += token
        socketio.emit("llm_stream", {"token": token})

    socketio.emit("llm_done", {"status": "completed"})
    generate_repport.repportLLM(full_text,  anomalies_df_to_text(row)
)

    return full_text

############## TRS ##############

def trs_prompt_diag(workflow, anomalies_df, trs: dict, period: dict) -> str:
    """
    Prompt TRS strict :
    - workflow nominal = référence absolue
    - sortie factuelle, concise
    - erreurs listées par step uniquement
    """

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
        for _, row in anomalies_df.iterrows():
            lines.append(
                f"Cycle {int(row['cycle'])} | "
                f"Machine {row['machine']} | "
                f"step Id {row.get('step_id', 'UNKNOWN')} | "
                f"Step Name {row.get('step_name', 'UNKNOWN')} | "
                f"Level {row.get('level', 'UNKNOWN')} | "
                f"Overrun {round(row.get('duration_overrun_s', 0), 2)} s | "
                f"MLScore {round(row.get('anomaly_score', 0), 3)}"
            )
        anomalies_str = "\n".join(lines)
        anomalies_str = "\n".join(lines)

    trs_value = trs.get("trs", trs)

    workflow_str = (
        workflow if isinstance(workflow, str)
        else json.dumps(workflow, ensure_ascii=False, indent=2)
    )

    return f"""
Tu es un expert industriel senior spécialisé en performance de lignes automatisées
et en analyse de workflows PLC / Grafcet.

Tu analyses une dérive TRS UNIQUEMENT à partir des données fournies.
Le WORKFLOW NOMINAL est la RÉFÉRENCE ABSOLUE de comparaison.

⚠️ RÈGLES ABSOLUES (À RESPECTER STRICTEMENT) :
- Réponds DIRECTEMENT par l’analyse demandée.
- N’écris AUCUNE consigne, commentaire ou méta-explication.
- Ne répète AUCUNE information fournie.
- N’invente RIEN.
- Ne reformule PAS les données.
- Toute analyse doit être reliée EXPLICITEMENT au workflow nominal.
- Toute estimation doit être JUSTIFIÉE par les écarts observés.
- Ne produis PAS de texte hors format.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKFLOW NOMINAL (RÉFÉRENCE UNIQUE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{workflow_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Période :
- Début : {period['start']}
- Fin   : {period['end']}

TRS (conformité workflow) : {trs_value}
Nombre d’anomalies : {anomalies_count}
Temps total perdu vs nominal : {total_lost_time} s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANOMALIES OBSERVÉES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{anomalies_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OBJECTIF DE L’ANALYSE (OBLIGATOIRE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tu dois analyser les STEPS en erreur ou en déphasage de cycle en te basant
STRICTEMENT sur la comparaison :

RÉEL ⟷ NOMINAL (workflow)

L’analyse doit obligatoirement :

1) Identifier les STEPS NON CONFORMES au workflow nominal
   (sur-durée, blocage, erreur PLC, désynchronisation).

2) Associer chaque step NON CONFORME à :
   - sa MACHINE
   - son rôle dans le workflow nominal
   - son type de dérive (temps / séquence / synchronisation / erreur)

3) Quantifier l’IMPACT SUR LA PRODUCTION en POURCENTAGE :
   - part estimée du temps perdu total imputable à chaque step
   - impact relatif sur le TRS (en %)
   ⚠️ Les pourcentages doivent être cohérents entre eux (total ≤ 100%).

4) Identifier le ou les STEPS LES PLUS IMPACTANTS :
   - ceux qui contribuent le plus à la perte de temps
   - ceux qui dégradent le plus la synchronisation du workflow

5) Réaliser une ANALYSE FINE DU WORKFLOW :
   - respect ou violation de l’ordre des machines
   - propagation de la dérive vers l’aval (effet domino)
   - sensibilité du cycle global à ce step

6) Proposer une ANALYSE TECHNIQUE ou une SOLUTION
   UNIQUEMENT si elle découle logiquement :
   - du step concerné
   - du type d’écart observé
   - de la structure du workflow nominal

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SORTIE OBLIGATOIRE — FORMAT STRICT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1) Diagnostic TRS
- Phrase unique, factuelle, orientée workflow.

2) Erreurs par step (LISTE SIMPLE OBLIGATOIRE)
- Une ligne = un step
- Format EXACT :
  Machine | Step | Type d’écart | Impact cycle | Impact production %

3) Steps les plus impactants
- Classement décroissant
- Machine | Step | Contribution à la perte totale (%)

4) Analyse workflow
- 3 à 5 lignes maximum
- Décrire comment les steps identifiés perturbent le cycle nominal

5) Actions ou analyse technique
- Liste courte
- Uniquement déduite des écarts observés

❌ Tout texte hors de ce format est INTERDIT.
❌ Toute supposition est INTERDITE.
❌ Toute répétition est INTERDITE.
""".strip()



def eval_prompt_trs(prompt, model, tokenizer, anomalies_df, period=None):
    anomalie = anomalies_df_to_text(anomalies_df)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    print(prompt)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=500,
            do_sample=False,          # 🔒 DÉTERMINISTE
            temperature=0.0,          # 🔒 PAS DE CRÉATIVITÉ
            repetition_penalty=1.05,  # léger anti-boucle
            no_repeat_ngram_size=4,   # empêche reformulation
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
    generate_repport.repportLLM(
        result,
        anomalie  # on passe le DF, pas le texte
    )

    return result
