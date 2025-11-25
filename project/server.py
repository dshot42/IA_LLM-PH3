from flask import Flask, request, jsonify
from flask_cors import CORS
from prompt_model import PhiChat
import threading
from learning_model import LoRATrainer

app = Flask(__name__)
CORS(app)

# Création de l'objet modèle
phi_chat = PhiChat(model_id="Phi-3-mini-4k-instruct")

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    user_input = data.get("prompt", "").strip()

    if not user_input:
        return jsonify({"reply": "Error: prompt is empty"})

    # Construction du prompt pour instruct
    prompt = f"USER: {user_input}\n"
    prompt += "ASSISTANT:"

    # Génération
    response_text = phi_chat.generate(prompt, max_new_tokens=100)

    return jsonify({"reply": response_text})
    
@app.route("/api/instruction", methods=["POST"])
def train_lora():
    data = request.get_json()
    prompt_input = data.get("prompt", "").strip()
    response_input = data.get("instruction", "").strip()


    # Lancer le fine-tuning dans un thread
    def run_training():
        trainer = LoRATrainer(output_dir="./lora_phi3")
        trainer.setup_lora()
        trainer.train_on_prompt(prompt_input, response_input, num_epochs=1, batch_size=1)

    threading.Thread(target=run_training).start()
      
    return jsonify({"status": "Fine-tuning LoRA XPU lancé en arrière-plan."})


if __name__ == "__main__":
    # Lancer le training test en arrière-plan
    def run_test_training():
        trainer = LoRATrainer(output_dir="./lora_phi3")
        trainer.traintest()

    threading.Thread(target=run_test_training).start()

    # Lancer le serveur Flask
    app.run(host="127.0.0.1", port=11434)