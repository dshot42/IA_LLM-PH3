import os
import os.path as op


class BaseConfig(object):
    BASEDIR = op.abspath(op.dirname(__file__))
    PROJECT_ROOT = BASEDIR

    MODEL_NAME = "models/phi2-mini"
    #TARGET_MODULES = ["self_attn.qkv_proj", "self_attn.o_proj"] #phi3
    TARGET_MODULES = ["q_proj", "v_proj"] #phi2/qwen
    
    LORA_R = 8
    LORA_ALPHA = 16
    LORA_DROPOUT = 0.05
    EPOCHS = 1
    BATCH_SIZE = 2
    LEARNING_RATE = 2e-5
    MAX_OUTPUT_TOKEN = 300
    TOP_P = 0.9
    TEMPERATURE = 0.7

    MAX_LENGTH = 512

    OUTPUT_DIR = "./lora_model"
    
    ####### RAG #######
    RAG_MODEL = "./models/all-MiniLM-L6-v2" # pour le embeded
    RAG_ARCHIVE_PATH = "./RAG/archive"    
    INDEX_FAISS = "./models/FAISS/"

Config = BaseConfig