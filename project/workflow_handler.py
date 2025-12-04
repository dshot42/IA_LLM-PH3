import os
import re
import eval

def load_workflow_files(folder_path):
    """
    Charge récursivement tous les fichiers d'un dossier et retourne un dictionnaire
    { chemin_complet_du_fichier : contenu_du_fichier }.
    """
    all_files_content = {}

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                all_files_content[file_path] = content
            except Exception as e:
                print(f"Could not read {file_path}: {e}")

    return all_files_content

folder_workflow = "./RAG/archive/industrie/ligne-PLC/" # prompt server http request with ligne name : get folder assigned at ligne  ! 


def workflow_search( user_ip, folder, query, model, tokenizer):
    MAX_CHARS = 10000  # Limite de caractères par section

    # -----------------------------
    # 1️⃣ Charger tous les fichiers de workflow
    # -----------------------------
    workflow_folder = os.path.join(folder_workflow, "workflow")
    workflow_files = load_workflow_files(folder_path=workflow_folder)
    workflow_content = "\n".join(workflow_files.values())

    # -----------------------------
    # 2️⃣ Charger les documents techniques
    # -----------------------------
    doc_folder = os.path.join(folder_workflow, "doc")
    docs_files = load_workflow_files(folder_path=doc_folder)
    docs_content = "\n".join(docs_files.values())[:MAX_CHARS]

    # -----------------------------
    # 3️⃣ Charger les logs et ne garder que les lignes pertinentes
    # -----------------------------
    log_folder = os.path.join(folder_workflow, "log")
    logs_files = load_workflow_files(folder_path=log_folder)
    relevant_logs = []

    for content in logs_files.values():
        for line in content.splitlines():
            if re.search(r"(error|fail|anomaly|warning)", line, re.IGNORECASE):
                # Extraire date/heure si disponible
                match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line)
                date_heure = match.group(0) if match else "date_heure_inconnue"
                relevant_logs.append(f"{date_heure} : {line}")

    logs_content = "\n".join(relevant_logs)[:MAX_CHARS]

    # -----------------------------
    # 4️⃣ Construire le prompt final
    # -----------------------------
    prompt = f"""
    Tu es un assistant français expert en workflow industriel - machine PLC.
    Analyse le workflow industriel, les documents techniques des machines et les logs d'exécution fournis.

    Pour chaque anomalie détectée, renvoie **uniquement** dans ce format strict** :

    date, heure => machine : erreur détectée lors de l'étape Step correspondante à la description "DescriptionErreur" dans la doc technique de la machine concernée

    - Step : étape du workflow où l'erreur apparaît tirée du workflow
    - date, heure : date et heure exacte tirée des logs
    - DescriptionErreur : description exacte tirée de la doc technique
    - machine : nom de la machine concernée tirée du workflow

    Si aucune anomalie n'est détectée, renvoie :
    aucune anomalie détectée

    Ne fournis aucun autre texte, explication, commentaire ou mise en forme Markdown.

    workflow industriel ligne PLC :
    {workflow_content}

    Documents techniques des machines de la ligne PLC :
    {docs_content}

    Logs de l'execution des machines de la ligne PLC (uniquement lignes pertinentes avec date/heure) :
    {logs_content}

    Question actuelle :
    {query}

    ⚠️ Réponse stricte comme indiqué ci-dessus.
    """.strip()

    print("### Workflow Prompt :", prompt)
    # -----------------------------
    # 5️⃣ Appel au modèle
    # -----------------------------
    
    response = eval.prompt_query(user_ip, prompt, model, tokenizer, with_context=True)

    return response
