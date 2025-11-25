import torch
import torch_directml
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from datasets import Dataset
from peft import LoraConfig, get_peft_model, TaskType
import random

class LoRATrainer:
    def __init__(self, model_name="phi-3-mini-4k-instruct", max_length=512, output_dir="./lora_phi3"):
        # Détection DirectML
        try:
            self.device = torch_directml.device()
            print(f"[INFO] Loading model {model_name} on DirectML (Intel Arc)...")
        except Exception as e:
            self.device = torch.device("cpu")
            print(f"[WARN] DirectML not available ({e}), fallback CPU. Loading model {model_name} on CPU...")

        self.model_name = model_name
        self.max_length = max_length
        self.output_dir = output_dir

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.model.to(self.device)

    def setup_lora(self, r=8, lora_alpha=16, target_modules=["self_attn.qkv_proj", "self_attn.o_proj"], lora_dropout=0.05):
        print("[INFO] Applying LoRA configuration...")
        lora_config = LoraConfig(
            r=r,
            lora_alpha=lora_alpha,
            target_modules=target_modules,
            lora_dropout=lora_dropout,
            bias="none",
            task_type=TaskType.CAUSAL_LM
        )
        self.model = get_peft_model(self.model, lora_config)
        self.model.to(self.device)
        print("[INFO] LoRA applied.")

    def train_on_prompt(self, prompt: str, response: str, num_epochs=1, batch_size=1, learning_rate=2e-3):
        """Fine-tune sur un seul exemple : prompt + réponse attendue"""
        dataset = Dataset.from_dict({"prompt": [prompt], "response": [response]})
        self.train_on_dataset(dataset, num_epochs=num_epochs, batch_size=batch_size, learning_rate=learning_rate)

    def train_on_dataset(self, dataset, num_epochs=1, batch_size=1, learning_rate=2e-3):
        """Fine-tune sur un dataset"""

        def tokenize(batch):
            full_text = batch["prompt"] + " " + batch["response"]
            tokens = self.tokenizer(
                full_text,
                truncation=True,
                max_length=self.max_length,
                padding="max_length"
            )
            tokens["labels"] = tokens["input_ids"].copy()
            return tokens

        tokenized_dataset = dataset.map(tokenize, batched=False)

        training_args = TrainingArguments(
            output_dir=self.output_dir,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=1,
            learning_rate=learning_rate,
            num_train_epochs=num_epochs,
            logging_steps=1,
            save_steps=10,
            save_total_limit=2,
            fp16=False,  # DirectML ne supporte pas fp16
            dataloader_drop_last=True
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_dataset
        )

        print("[INFO] Starting fine-tuning on DirectML..." if "DirectML" in str(self.device) else "[INFO] Starting fine-tuning on CPU...")
        trainer.train()
        print(f"[INFO] Saving LoRA model to {self.output_dir}...")
        self.model.save_pretrained(self.output_dir)
        self.tokenizer.save_pretrained(self.output_dir)
        print("[INFO] Training Done!")

    def traintest(self, num_epochs=1, batch_size=1, learning_rate=2e-3):
        anomalies_pool = [
            "fuite huile", "calaminage des pistons", "verrouillage pompe",
            "problème hydraulique", "fuite gaz", "overheating",
            "capteur défaillant", "verrouillage sécurité", "pression basse",
            "vibration excessive", "courroie cassée", "lubrification insuffisante",
            "surchauffe moteur", "erreur électronique"
        ]

        num_machines = 50
        machines = [f"{random.choice(['A','B','C','D','E','F'])}{random.randint(10,99)}.{random.randint(1,9)}" for _ in range(num_machines)]

        def generate_dataset(machines, anomalies_pool, min_anomalies=3, max_anomalies=5):
            dataset_entries = []
            for machine in machines:
                num_anomalies = random.randint(min_anomalies, max_anomalies)
                selected_anomalies = random.sample(anomalies_pool, num_anomalies)
                response = ", ".join([f"X{i+1}:{a}" for i,a in enumerate(selected_anomalies)])
                prompt = f"anomalies machine {machine}"
                dataset_entries.append({"prompt": prompt, "response": response})
            return Dataset.from_list(dataset_entries)

        dataset = generate_dataset(machines, anomalies_pool)
        print("[INFO] Running training test...")
        self.train_on_dataset(dataset, num_epochs=num_epochs, batch_size=batch_size, learning_rate=learning_rate)