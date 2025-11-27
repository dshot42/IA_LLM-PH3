from flask import Flask, request, jsonify
from flask_cors import CORS
import model as model_utils
import eval
from config import Config
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig


# === Flask ===
app = Flask(__name__)
CORS(app)

# === Routes ===
@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    prompt = data.get("prompt", "")
    print("prompt : " + prompt)
    response_text = eval.faiss_search(prompt, model, tokenizer)
    return jsonify({"reply": response_text})

# === Main ===
if __name__ == "__main__":
    # === Charger le tokenizer et le modèle une seule fois ===
    print(" --- Loading Models...")
    tokenizer = model_utils.load_tokenizer()
    model = model_utils.load_model_with_qlora()
    '''
    model = AutoModelForCausalLM.from_pretrained(
        Config.MODEL_NAME,
        device_map="auto"    )
    '''
    print(" --- Model with QLoRA Loaded ...")
    # === Lancer le serveur Flask ===
    app.run(host="127.0.0.1", port=11434)
