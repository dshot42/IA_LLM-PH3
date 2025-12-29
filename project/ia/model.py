from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model
from config import Config
import torch


from llama_cpp import Llama

def llm():
    return Llama(
    model_path=Config.MODEL_NAME,
    n_ctx=4096,
    n_threads=8,
    n_batch=128,
    temperature=0.2,
    top_p=0.8,
    top_k=40,
)


def load_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME, use_fast=True, trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return tokenizer

def load_model_with_sft():
    model = AutoModelForCausalLM.from_pretrained(
        Config.MODEL_NAME,
        device_map="auto"
    )

    model.print_trainable_parameters()

    return model

def load_model_with_lora():
    model = load_standard_model()
    
    lora_config = LoraConfig(
        r=Config.LORA_R,
        lora_alpha=Config.LORA_ALPHA,
        target_modules=Config.TARGET_MODULES,
        lora_dropout=Config.LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model

def load_standard_model(load_in_4bit=True, load_in_8bit=False, double_quant=True, compute_dtype="float16", quant_type="nf4"):
    bnb_config = None
    if load_in_4bit or load_in_8bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=double_quant,
            bnb_4bit_quant_type=quant_type
        )

    model = AutoModelForCausalLM.from_pretrained(
        Config.MODEL_NAME,
        device_map=Config.DEVICE_MAP,
        #quantization_config=bnb_config, #gpu uniquement
        dtype=compute_dtype,
        #trust_remote_code=True,
        attn_implementation="eager",   # IMPORTANT → pas "attn_impl"
    )
    return model


def load_model_with_qlora(load_in_4bit=True, load_in_8bit=False, double_quant=True, compute_dtype="float16", quant_type="nf4"):
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=load_in_4bit,
        load_in_8bit=load_in_8bit,
        bnb_4bit_use_double_quant=double_quant,
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_quant_type=quant_type
    )

    model = AutoModelForCausalLM.from_pretrained(
        Config.MODEL_NAME,
        device_map="auto",
        quantization_config=bnb_config
    )
    #model = AutoModelForCausalLM.from_pretrained(Config.MODEL_NAME).to("cpu")

    lora_config = LoraConfig(
        r=Config.LORA_R,
        lora_alpha=Config.LORA_ALPHA,
        target_modules=Config.TARGET_MODULES,
        lora_dropout=Config.LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)

    # 3) Maintenant tu peux
    model.print_trainable_parameters()


    return model

'''
def load_model_directml():
    dml = torch_directml.device()

    model = AutoModelForCausalLM.from_pretrained(
        Config.MODEL_NAME,
        torch_dtype=torch.float16,  # float16 compatible DirectML
        low_cpu_mem_usage=True
    )

    return model.to(dml)
'''