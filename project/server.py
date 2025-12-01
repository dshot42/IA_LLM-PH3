import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import model as model_utils
import eval
from config import Config
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import history_handler

# === Flask ===
app = Flask(__name__)
CORS(app)

# === Routes ===
@app.route("/api/generate", methods=["POST"])
def generate():
    user_ip = get_user_ip(request)
    data = request.get_json()
    prompt = data.get("prompt", "")
    print("prompt : " + prompt)
    response_text = eval.faiss_search(user_ip, prompt, model, tokenizer)
    return jsonify({"reply": response_text})

@app.route("/api/prompt/image", methods=["POST"])
def image():
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


# === Main ===
if __name__ == "__main__":
    # === Charger le tokenizer et le modèle une seule fois ===
    print(" --- Loading Models...")
    tokenizer = model_utils.load_tokenizer()
    #model = model_utils.load_model_with_qlora()
        
    model = model_utils.load_standard_model()
    
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

    app.run(host="0.0.0.0", port=11434)
