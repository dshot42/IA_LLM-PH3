import os
import torch
import io
from config import Config
import faiss_handler
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import base64
import history_handler
import  web_search_handler
import os.path as op

folder_workflow = op.join(Config.RESSOURCES_DIR,"industrie/ligne_PLC-advanced") 


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



def workflow_search( user_ip, racine_folder, query, model, tokenizer):
    MAX_CHARS = 100000  # Limite de caractères par section

    # -----------------------------
    # 1️⃣ Charger tous les fichiers de workflow
    # -----------------------------
    workflow_folder = os.path.join(racine_folder, "workflow")
    workflow_files = load_workflow_files(folder_path=workflow_folder)
    workflow_content = "\n".join(workflow_files.values())

    # -----------------------------
    # 2️⃣ Charger les documents techniques
    # -----------------------------
    doc_folder = os.path.join(racine_folder, "doc")
    docs_files = load_workflow_files(folder_path=doc_folder)
    docs_content = "\n".join(docs_files.values())

    # -----------------------------
    # 3️⃣ Charger les logs et ne garder que les lignes pertinentes
    # -----------------------------
    log_folder = os.path.join(racine_folder, "log")
    logs_files = load_workflow_files(folder_path=log_folder)
    logs_content = "\n".join(logs_files.values())

    # -----------------------------
    # 4️⃣ Construire le prompt final
    # -----------------------------
    prompt = f"""
    Tu es un assistant français expert en analyse de workflow industriel sur lignes PLC multi-machines.
    Ta mission : analyser précisément les logs d'exécution en les confrontant strictement au workflow et à la documentation technique. 
    Aucune information extérieure ne doit être inventée.

    === Données disponibles ===
    Workflow industriel :
    {workflow_content}

    Documentation technique des machines :
    {docs_content}

    Logs d'exécution (extraits horodatés pertinents) :
    {logs_content}

    Question :
    {query}

    === Ce que tu dois produire ===
    Un compte rendu structuré uniquement sur la base des données fournies, détaillant pour chaque événement concerné par la Question :

    - **Machine :** nom de la machine impliquée
    - **Step :** ID + nom + description officielle tirée de la documentation technique
    - **Timestamp :** début et fin (selon les logs disponibles)
    - **Statut :** OK / ERROR / WARNING
    - **Code erreur :** explication issue de la documentation technique (si disponible)
    - **Analyse workflow :** 
        • cohérence par rapport au step attendu  
        • éventuel dépassement de durée / déphasage entre machines  
        • anomalie ou transition non conforme au grafcet  
    - **Impact production :** conséquence possible sur le cycle global

    === Contraintes ===
    - Ne pas répéter le prompt, les logs, ni le workflow.
    - Ne générer aucune information absente des données.
    - Répondre STRICTEMENT à la Question actuelle et pas à autre chose.
    - Ne commenter que les événements réellement présents dans les logs.

    Réponse attendue : un rapport clair, structuré, concis et orienté terrain.
    """


    # -----------------------------
    # 5️⃣ Appel au modèle
    # -----------------------------
    #print("### workflow prompt : "+ prompt)
    response = prompt_query(user_ip, prompt, model, tokenizer)
    return response

def prompt_query(user_ip, prompt, model, tokenizer):
          
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device) # important 
   
    def run_generation():
        with torch.no_grad():
            return model.generate(
                **inputs,
                max_new_tokens=500,
                do_sample=False,
                repetition_penalty=1.08,
                no_repeat_ngram_size=3
            )

    with ThreadPoolExecutor() as executor:
        future = executor.submit(run_generation)
        try:
            output = future.result(timeout=1000)  # timeout
            decoded = tokenizer.decode(output[0], skip_special_tokens=True)
            print("### result : " +decoded[len(prompt):].strip())
            return decoded[len(prompt):].strip()
        except TimeoutError:
            return f"⏱️ La génération a dépassé le délai imparti ({1000} sec)"
        