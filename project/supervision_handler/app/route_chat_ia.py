import os
from flask import Blueprint, jsonify, request, Response,send_file,abort
from flask_cors import CORS
import ia.model as model_utils
import ia.eval as eval
from ia.sql_handler import Database
from supervision_handler.app.extensions import tokenizer, model


chat_ia = Blueprint("chat_ia", __name__, url_prefix="/chat_ia")

# === Routes ===
@chat_ia.post("/generate")
def generate_faiss_prompt():
    user_ip = get_user_ip(request)
    data = request.get_json()
    prompt = data.get("prompt", "")
    print("prompt : " + prompt)
    response_text = eval.faiss_search(user_ip, prompt, model, tokenizer)
    return jsonify({"reply": response_text})

@chat_ia.post("/sql")
def generate_sql_prompt():
    user_ip = get_user_ip(request)
    data = request.get_json()
    prompt = data.get("prompt", "")
    print("prompt : " + prompt)
    db = Database()
    response_text = db.prompt_sql_query(user_ip, prompt, model, tokenizer)
    return Response(response_text, mimetype="text/plain")

        
@chat_ia.post("/prompt/image")
def generate_image_prompt():
    user_ip = get_user_ip(request)
    data = request.get_json()
    prompt = data.get("prompt", "")
    if prompt.startswith("data:image"):
        prompt = prompt.split(",")[1]

    response_text = eval.prompt_image(user_ip, prompt, model, tokenizer)
    return jsonify({"reply": response_text})

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




