import torch
import torch_directml
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from datasets import Dataset
from peft import LoraConfig, get_peft_model, TaskType

class LoRATrainer:
    def __init__(self, model_name="llm_model"):
        # DirectML
        try:
            self.device = torch_directml.device()
            print("[INFO] DirectML détecté, utilisation du GPU Intel Arc")
        except Exception as e:
            self.device = torch.device("cpu")
            print(f"[WARN] DirectML non disponible ({e}), fallback CPU")

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Crée le modèle AVANT de le déplacer
        self.model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16)

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            #self.tokenizer.add_special_tokens({'pad_token': '[PAD]'})

        # Appliquer LoRA via la méthode de la classe LoRATrainer
        self.model = self.setup_lora().to(self.device)  # setup_lora doit prendre le modèle en argument et retourner le modèle LoRA

        # Déplacer le modèle sur le device (GPU DirectML si dispo)
        self.model =self. model.to(self.device)
  
        print("[INFO] Modèle chargé sur le GPU Intel Arc avec succès")
        

    def setup_lora(self, r=4, lora_alpha=16, target_modules=["self_attn.qkv_proj", "self_attn.o_proj"], lora_dropout=0.05):
        print("[INFO] Applying LoRA...")

        # Gradient checkpointing pour réduire la VRAM
        self.model.gradient_checkpointing_enable()
        #use_cache=True` is incompatible with gradient checkpointing. Setting `use_cache=False`.

        # Config LoRA : seuls les LoRA weights en FP16
        lora_config = LoraConfig(
            r=r,
            lora_alpha=lora_alpha,
            target_modules=target_modules,
            lora_dropout=lora_dropout,
            bias="none",
            task_type=TaskType.CAUSAL_LM
        )

        return get_peft_model(self.model, lora_config) 
        #.to(self.device) decommenté pour gpu sinon cpu

    def train_on_prompt(self, prompt: str, response: str):
            """Fine-tune sur un seul exemple : prompt + réponse attendue"""
            dataset = Dataset.from_dict({"prompt": [prompt], "response": [response]})
            self.train_on_dataset(dataset)

    def train_on_dataset(self, dataset, num_epochs=1, batch_size=1, learning_rate=2e-3):
        """
        Fine-tune le modèle LoRA sur un dataset fourni, avec affichage du device utilisé.

        Args:
            dataset (Dataset): Dataset HuggingFace contenant les colonnes "prompt" et "response".
            num_epochs (int): Nombre d'époques d'entraînement.
            batch_size (int): Taille de batch par GPU.
            learning_rate (float): Learning rate.
        """

        # 1️⃣ Tokenization
        def tokenize(batch):
            full_text = f"### Instruction:\n{batch['prompt']}\n\n### Response:\n{batch['response']}"
            tokens = self.tokenizer(
            full_text,
            truncation=True,
            padding="max_length",
            max_length=512
            )
            tokens["labels"] = tokens["input_ids"].copy()
            return tokens

        tokenized_dataset = dataset.map(tokenize, batched=False)

        # Arguments d'entraînement
        training_args = TrainingArguments(
            output_dir="./lora_llm_model",
            per_device_train_batch_size=batch_size,  # int
            gradient_accumulation_steps=4,           # int
            learning_rate=learning_rate,             # float
            num_train_epochs=num_epochs,             # int
            fp16=False                               # bool
        )

        #  Création du Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_dataset
        )

        #  Affichage du device utilisé
        print("[DEBUG] GPU/CPU: ", next(self.model.parameters()).device)

        #  Lancer l'entraînement
        print("[INFO] Starting fine-tuning...")
        trainer.train()

        #  Sauvegarde du modèle et du tokenizer
        print("[INFO] Saving LoRA model...")

        trainer.model.save_pretrained("./lora_llm_model")
        self.tokenizer.save_pretrained("./lora_llm_model")

        print("[INFO] Training Done!")

     