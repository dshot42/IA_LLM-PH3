import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

class PhiChat:
    def __init__(self, model_id="llm_model", lora_dir=None, max_length=2048):
        self.device = torch.device("cpu")
        print(f"[INFO] Using device: {self.device}")

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Modèle
        print(f"[INFO] Loading model {model_id}...")
        self.model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)

        # Charger LoRA si disponible
        if lora_dir:
            print(f"[INFO] Loading LoRA from {lora_dir}...")
            self.model = PeftModel.from_pretrained(self.model, lora_dir)
            # Merge LoRA pour CPU
            self.model = self.model.merge_and_unload()

        self.model.eval()
        self.model.to(self.device)
        print("[INFO] Model ready!")

    def generate(self, prompt, max_new_tokens=150, temperature=0.8, top_p=0.9):
        # Tokenization
        eval.evaluate_model(model, tokenizer)

    def generate_from_machines(self, machines):
        """
        Génère un prompt automatiquement à partir d'une liste de machines/anomalies.
        machines = [{"name": "Machine 1", "anomaly": "calaminage des pistons"}, ...]
        """
        report_text = "\n".join([f"{m['name']} : {m['anomaly']}" for m in machines])
        prompt = f"USER: Liste toutes les machines présentant des anomalies dans le rapport suivant :\n{report_text}\nASSISTANT:"
        return self.generate(prompt)
