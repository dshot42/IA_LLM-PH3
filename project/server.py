import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import model as model_utils
import eval
from config import Config
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import history_handler
from sql_handler import Database

# === Flask ===
app = Flask(__name__)
CORS(app)

# === Routes ===
@app.route("/api/generate", methods=["POST"])
def generate_faiss_prompt():
    user_ip = get_user_ip(request)
    data = request.get_json()
    prompt = data.get("prompt", "")
    print("prompt : " + prompt)
    response_text = eval.faiss_search(user_ip, prompt, model, tokenizer)
    return jsonify({"reply": response_text})

@app.route("/api/sql", methods=["POST"])
def generate_sql_prompt():
    user_ip = get_user_ip(request)
    data = request.get_json()
    prompt = data.get("prompt", "")
    print("prompt : " + prompt)
    db = Database()
    response_text = db.prompt_sql_query(user_ip, prompt, model, tokenizer)
    return Response(response_text, mimetype="text/plain")

        
@app.route("/api/prompt/image", methods=["POST"])
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



# === Main ===
if __name__ == "__main__":
    # === Charger le tokenizer et le modèle une seule fois ===
    print(" --- Loading Models...")
    tokenizer = model_utils.load_tokenizer()
    #model = model_utils.load_model_with_qlora()       
    model = model_utils.load_standard_model()
    
    app.run(host="0.0.0.0", port=11434)
