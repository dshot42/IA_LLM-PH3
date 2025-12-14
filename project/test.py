import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import model as model_utils
import eval
from config import Config
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import history_handler
from sql_handler import Database
import workflow_handler



def get_user_ip(request):
    user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if user_ip and "," in user_ip:
        # Si plusieurs IPs (proxy), on prend la première
        user_ip = user_ip.split(",")[0].strip()
    return user_ip



def test_prompt ():
    query = "quel est le numero france travail de monsieur dubost come "
    print("prompt : " + query) 
    response_text = eval.faiss_search("none", query, model, tokenizer)


    query = "quel est la Somme des montants total  des factures pour le client: Maxime Durand ?"
    print("prompt : " + query) 
    response_text = eval.faiss_search("none", query, model, tokenizer)
    

    # === Lancer le serveur Flask ===
    query = "quel est le nom de la planete ou le petit prince a rencontré l'ivrogne ?" 
    # attendu :chunk passage du petit prince 

    print("prompt : " + query) 
    response_text = eval.faiss_search("none", query, model, tokenizer)
    
    query = "explique moi la loi de la relativité général ?"
    print("prompt : " + query)
    response_text = eval.faiss_search("none", query, model, tokenizer) 
    # attendu : aucun faiss trouvé -> prompt sur LLM ou recherche internet



# === Main ===
if __name__ == "__main__":
    # === Charger le tokenizer et le modèle une seule fois ===
    print(" --- Loading Models...")
    tokenizer = model_utils.load_tokenizer()
    model = model_utils.load_standard_model()
      
   # test_prompt()
   
    folder = os.path.join(Config.PROJECT_ROOT, workflow_handler.folder_workflow)
    workflow_handler.workflow_search("none",folder, "y a t'il eu des erreur / anomalie sur les machines de la ligne PLC suivant le Workflow industriel ?",model, tokenizer)


    db = Database()
    db.prompt_sql_query("none","afficher moi la liste des informations des employee assigné au restaurant : Le Meurice Alain Ducasse",model, tokenizer)


