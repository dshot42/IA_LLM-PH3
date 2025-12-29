import io
import base64
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from config import Config
from ia.faiss.faiss_handler import retrieve
from ia.history_handler import filter_relevant_history, add_user_query
from ia.web_search_handler import searchWeb

from ia.generate_repport import repportLLM
from ia.generate_repport_trs import  repportLLM_TRS
from config import Config
from ia.faiss.faiss_handler import retrieve

# =========================================================
# CHAT TEMPLATE GGUF
# =========================================================
def build_chat_prompt(system, user):
    return f"""<|system|>
{system}
<|end|>

<|user|>
{user}
<|end|>

<|assistant|>
"""


# =========================================================
# GGUF GENERATION
# =========================================================
def run_gguf_generation(model, prompt):
    result = model(
        prompt,
        max_tokens=Config.MAX_OUTPUT_TOKEN,
        temperature=Config.TEMPERATURE,
        top_p=Config.TOP_P,
        top_k=Config.TOP_K,
        repeat_penalty=1.08,
        stop=["<|end|>"]
    )
    return result["choices"][0]["text"].strip()


# =========================================================
# FAISS + RAG
# =========================================================
def faiss_search(user_ip, query, model, workeflow):
    retrieved = retrieve(user_ip="none",query = query, workeflow = workeflow)

    if not retrieved:
        print("⚠️ Aucun chunk pertinent (score < threshold). Fallback vers LLM brut.")
        return prompt_query(user_ip, query, model)

    context = "\n\n".join([
        f"Texte: {r['text']}...\n"
        f"Chemin: {r['metadata'].get('path','inconnu')}\n"
        f"Source: {r['metadata'].get('source','inconnu')}\n"
        f"Page: {r['metadata'].get('page','?')}\n"
        f"Score: {round(r.get('score', 0), 3)}"
        for r in retrieved
    ])

    system_prompt = """Tu es un assistant français RAG.
        Tu dois répondre UNIQUEMENT à partir du contexte fourni.
        Aucune information extérieure ne doit être ajoutée.
        Réponse factuelle, concise, directe.
        """

    user_prompt = f"""=== Contexte ===
{context}

=== Question ===
{query}

Règles :
- Ne répète pas le contexte
- Ne reformule pas la question
- Pas de Markdown
- Pas d’explication
"""

    prompt = build_chat_prompt(system_prompt, user_prompt)

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_gguf_generation, model, prompt)
        try:
            return future.result(timeout=Config.SERVER_TIMEOUT)
        except TimeoutError:
            return f"⏱️ La génération a dépassé le délai imparti ({Config.SERVER_TIMEOUT} sec)"


# =========================================================
# PROMPT DIRECT (HISTORIQUE + WEB)
# =========================================================
def prompt_query(user_ip, query, model):
    history = filter_relevant_history(user_ip, query)
    add_user_query(user_ip, query)

    history_text = ""
    if history:
        history_text = "\n".join([f"- {h}" for h in history])

    web_results = searchWeb(query)
    web_text = ""
    if web_results:
        web_text = "\n".join([
            f"{r['title']} | {r['url']}\n{r.get('snippet','')}"
            for r in web_results
        ])

    system_prompt = """Tu es un assistant français.
Tu dois répondre UNIQUEMENT à partir des éléments fournis.
Réponse courte, précise, directe.
"""

    user_prompt = f"""
Historique pertinent :
{history_text if history_text else "Aucun"}

Contexte web :
{web_text if web_text else "Aucun"}

Question :
{query}

Règles strictes :
- Ne pose pas de questions
- Ne répète pas la question
- Ne mentionne pas l’historique
- Ne commente rien
- Pas de Markdown
"""

    prompt = build_chat_prompt(system_prompt, user_prompt)

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_gguf_generation, model, prompt)
        try:
            return future.result(timeout=Config.SERVER_TIMEOUT)
        except TimeoutError:
            return f"⏱️ La génération a dépassé le délai imparti ({Config.SERVER_TIMEOUT} sec)"


# =========================================================
# EVAL PROMPT SIMPLE
# =========================================================
def eval_prompt(prompt, model):
    system_prompt = "Tu es un assistant français."
    final_prompt = build_chat_prompt(system_prompt, prompt)

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_gguf_generation, model, final_prompt)
        try:
            return future.result(timeout=2000)
        except TimeoutError:
            return f"⏱️ La génération a dépassé le délai imparti (2000 sec)"


def eval_prompt_anomaly_gguf(
    system_prompt: str,
    user_prompt: str,
    model,
    anomalie: dict
):
    # ============================================================
    # RAG
    # ============================================================
    query = (
        f"Machine {anomalie['machine']} "
        f" {anomalie['stepId']} "
        f" {anomalie['stepName']} "
    )
    
    print("RAG QUERY : " + query)

    retrieved = retrieve(
        user_ip="none",
        query=query,
        workflow=True
    )

    if retrieved:
        rag_block = (
            "DOCUMENTATION TECHNIQUE DISPONIBLE (USAGE STRICTEMENT FACTUEL)\n"
            "Les extraits suivants peuvent être utilisés UNIQUEMENT s’ils "
            "sont directement applicables aux règles déclenchées.\n\n"
            + "\n\n".join([
                f"- Extrait :\n{r['text']}\n"
                f"Source : {r['metadata'].get('source','?')} | "
                f"Page : {r['metadata'].get('page','?')} | "
                f"Score : {round(r.get('score', 0), 3)}"
                for r in retrieved
            ])
        )
    else:
        rag_block = (
            "Aucune documentation technique pertinente disponible.\n"
            "L’analyse DOIT être basée exclusivement sur les règles déclenchées "
            "et les observations factuelles."
        )

    # ============================================================
    # PROMPT FINAL UTILISATEUR
    # ============================================================
    final_prompt = f"""
{system_prompt}

{user_prompt}

===========================
CONTEXTE DOCUMENTAIRE
===========================
{rag_block}

===========================
RÈGLES ABSOLUES D’ANALYSE
===========================
- Analyse STRICTEMENT factuelle
- Aucune hypothèse non déduite des données
- Si erreur PLC explicite : analyse événementielle prioritaire
- Les durées et déphasages sont des CONSÉQUENCES, jamais des causes
- Si données insuffisantes : le dire explicitement

===========================
FORMAT DE SORTIE STRICT
===========================
- Rapport structuré
- Phrases courtes
- Chiffres systématiques
- Aucun commentaire hors données
"""

    # ============================================================
    # APPEL LLM — GGUF VERROUILLÉ
    # ============================================================
    print ("[RUN LLM] Wait Anomaly Result ")
    print(final_prompt)
    output = model.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    """
                    LANGUE DE SORTIE OBLIGATOIRE : FRANÇAIS UNIQUEMENT.

                    INTERDICTION ABSOLUE :
                    - Toute utilisation de mots, phrases ou expressions en anglais.
                    - Toute sortie partiellement ou totalement en anglais est STRICTEMENT INTERDITE
                    et sera considérée comme INVALIDE.

                    RÈGLE DE CONFORMITÉ :
                    - La réponse doit être intégralement rédigée en français.
                    - Les termes techniques doivent être traduits ou explicités en français.
                    - Aucun anglicisme, acronyme ou terme non traduit n’est autorisé.

                    UTILISATION DE DOCUMENTATION TECHNIQUE :
                    - Si la réponse s’appuie sur une documentation technique disponible,
                    tu DOIS obligatoirement le préciser explicitement sous la forme suivante :

                    « Selon la documentation technique de référence : [nom du document] »

                    Toute réponse ne respectant pas strictement ces règles est considérée comme NON CONFORME.

                """
                 
                )
            },
            {
                "role": "user",
                "content": final_prompt
            }
        ],
        temperature=0.1,   # 🔒 factuel
        top_p=0.8,
        top_k=40,
        repeat_penalty=1.1,
        max_tokens=2500
    )

    result = output["choices"][0]["message"]["content"].strip()

    if not result or len(result) < 50:
        raise RuntimeError("LLM output invalide ou vide (Anomaly)")

    print ("[RUN LLM] SUCCESS Anomaly Result length => ",  len(result) )
 
    return repportLLM(result, anomalie, final_prompt)

########## TRS ############

def eval_prompt_trs_gguf(
    prompt: str,
    trs: dict,
    impact: list,
    dateStart,
    dateEnd,
    model
):

    # ============================================================
    # CONTEXTE STRUCTURÉ POUR LE LLM (DONNÉES)
    # ============================================================
    trs_block = f"""
TRS GLOBAL :
- TRS            : {trs['trs']}
- Performance    : {trs['performance']}
- Qualité        : {trs['quality']}
- Steps analysés : {trs['totalSteps']}
- Steps NOK      : {trs['badSteps']}
- Temps nominal  : {trs['totalTheoreticalTimeS']} s
- Temps réel     : {trs['totalRealTimeS']} s
"""

    if impact:
        impact_block = "\n".join([
            f"- Machine={i['machineCode']} | Step={i['stepCode']} | "
            f"Occ={i['occurrences']} | Overrun={i['totalOverrunS']} s | "
            f"ImpactTRS={i['impactPercentTRS']} % | "
            f"Danger={i['dangerScore']} | "
            f"Renforcement={i['reinforcing']}"
            for i in impact.values()
        ])
    else:
        impact_block = (
            "Aucune anomalie mesurée disponible.\n"
            "Toute conclusion doit refléter explicitement cette absence de données."
        )

    # ============================================================
    # PROMPT FINAL (UTILISATEUR)
    # ============================================================
    final_prompt = f"""
{prompt}

===========================
PÉRIODE ANALYSÉE
===========================
{dateStart} → {dateEnd}

===========================
DONNÉES TRS MESURÉES
===========================
{trs_block}

===========================
IMPACTS PAR STEP / MACHINE
===========================
{impact_block}

===========================
RÈGLES D’ANALYSE STRICTES
===========================
- Analyse UNIQUEMENT basée sur les données fournies
- Aucune hypothèse non déduite des chiffres
- Aucun ajout externe
- Aucun conseil ou recommandation
- Comparaison STRICTE réel vs nominal
- Tous les impacts DOIVENT être chiffrés (temps et %)
- Identifier UNIQUEMENT les causes MAJEURES
- Si données insuffisantes : le dire explicitement

===========================
FORMAT DE SORTIE OBLIGATOIRE
===========================
ANOMALIES MAJEURES :
1. <description> — <temps>s — <impact %>
2. <description> — <temps>s — <impact %>
3. <description> — <temps>s — <impact %>

CONTRIBUTION CUMULÉE :
- <valeur %>

NATURE DE LA DÉGRADATION :
- STRUCTURELLE ou PONCTUELLE

CONCLUSION FACTUELLE :
- Ligne 1
- Ligne 2
- Ligne 3
"""

    # ============================================================
    # APPEL LLM (GGUF VERROUILLÉ)
    # ============================================================
    print ("[RUN LLM] Wait TRS Result ")

    output = model.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    """
                    LANGUE DE SORTIE OBLIGATOIRE : FRANÇAIS UNIQUEMENT.
                    INTERDICTION ABSOLUE :
                    - anglais
                    TOUTE SORTIE CONTENANT DE L’ANGLAIS EST CONSIDÉRÉE COMME INVALIDE.
                """
                )
            },
            {
                "role": "user",
                "content": final_prompt
            }
        ],
        temperature=0.1,   # 🔒 TRÈS factuel
        top_p=0.8,
        top_k=40,
        repeat_penalty=1.1,
        max_tokens=2500
    )

    result = output["choices"][0]["message"]["content"].strip()

    if not result or len(result) < 50:
        raise RuntimeError("LLM output invalide ou vide (TRS)")

    print ("[RUN LLM] SUCCESS TRS Result length => ",  len(result) )

    # ============================================================
    # RAPPORT (INCHANGÉ)
    # ============================================================
    return repportLLM_TRS(
        result,
        trs,
        impact,
        dateStart,
        dateEnd,
        final_prompt
    )
