from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch
import torch_directml

class PhiChat:
    def __init__(self, model_id="Phi-3-mini-4k-instruct", lora_dir="lora_phi3", lora_multiplier=10.0):
        """
        Initialise le modèle Phi pour DirectML (Intel Arc), avec LoRA appliquée en priorité.
        lora_multiplier : facteur multiplicatif pour augmenter l'impact de la LoRA
        """
        try:
            self.device = torch_directml.device()
            print("[INFO] DirectML détecté, utilisation du GPU Intel Arc")
        except Exception as e:
            self.device = torch.device("cpu")
            print(f"[WARN] DirectML non disponible ({e}), fallback CPU")

        self.model_id = model_id
        self.lora_dir = lora_dir
        self.lora_multiplier = lora_multiplier

        print(f"[INFO] Loading base model {model_id}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, device_map=None)

        if lora_dir is not None:
            print(f"[INFO] Loading LoRA from {lora_dir} and applying on top of base model...")
            self.model = PeftModel.from_pretrained(self.model, lora_dir)

            # MULTIPLY LORA WEIGHTS
            print(f"[INFO] Multiplying LoRA weights by {lora_multiplier} for priority")
            for name, param in self.model.named_parameters():
                if "lora" in name:
                    param.data *= lora_multiplier

        self.model.to(self.device)
        self.model.eval()
        print("[INFO] Model ready!")

    def generate(self, prompt, max_new_tokens=100, temperature=0.7):
        """
        Génère du texte sur DirectML (ou CPU fallback) avec LoRA prioritaire
        """
        prompt = prompt.strip()
        if not prompt:
            return "Error: prompt is empty"

        if not prompt.startswith("USER:"):
            prompt = f"USER: {prompt}\nASSISTANT:"

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=4096
        ).to(self.device)

        if inputs.input_ids.shape[1] == 0:
            return "Error: input_ids is empty after tokenization"

        try:
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.2
            )
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            return f"Error during generation: {str(e)}"


# Exemple d'utilisation :
# phi_chat = PhiChat(lora_dir="lora_phi3", lora_multiplier=100.0)
# print(phi_chat.generate("Anomalies machine B32.12"))