import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForSeq2Seq
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, TaskType

# =====================
# CONFIG
# =====================
MODEL_NAME = "llm_model"
DATASET_PATH = "dataset/machines_anomalies.json"
OUTPUT_DIR = "lora_model"
MAX_LENGTH = 256
BATCH_SIZE = 2
EPOCHS = 3
LR = 5e-4

# =====================
# LOAD DATASET
# =====================
dataset = load_dataset("json", data_files=DATASET_PATH)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# =====================
# PREPROCESS
# =====================
def preprocess(example):
    prompt = example["instruction"] + "\n" + example["input"]
    target = example["output"]
    model_inputs = tokenizer(
        prompt,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True
    )
    labels = tokenizer(
        target,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True
    )["input_ids"]
    model_inputs["labels"] = labels
    return model_inputs

tokenized_dataset = dataset.map(
    preprocess,
    remove_columns=dataset["train"].column_names if "train" in dataset else dataset.column_names
)

# =====================
# DATA COLLATOR
# =====================
data_collator = DataCollatorForSeq2Seq(tokenizer, padding=True)

# =====================
# LOAD MODEL + LORA
# =====================
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["self_attn.qkv_proj", "self_attn.o_proj"],
    lora_dropout=0.05,
    task_type=TaskType.CAUSAL_LM
)

model = get_peft_model(model, lora_config)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# =====================
# TRAINING ARGS
# =====================
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=BATCH_SIZE,
    num_train_epochs=EPOCHS,
    learning_rate=LR,
    logging_steps=10,
    save_strategy="epoch",
    remove_unused_columns=False,
)

# =====================
# TRAINER
# =====================
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"] if "train" in tokenized_dataset else tokenized_dataset,
    tokenizer=tokenizer,
    data_collator=data_collator
)

# =====================
# TRAIN
# =====================
trainer.train()
model.save_pretrained(OUTPUT_DIR)
print("[INFO] Entraînement terminé et LoRA sauvegardé !")
