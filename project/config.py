import os
import os.path as op


class BaseConfig(object):
    BASEDIR = op.abspath(op.dirname(__file__))
    PROJECT_ROOT = BASEDIR

    DEVICE_MAP="cpu" # cuda , xpu
    #MODEL_NAME ="./models/Phi-3-small-128k-instruct" # CUDA gros model a faire tourner en 4bit ou 8 via GPU
    MODEL_NAME ="./models/Phi-3-mini-128k-instruct" # CPU "models/phi2-mini| Phi-3-mini-128k-instruct | Llama-3.1-8B"

    TARGET_MODULES = ["self_attn.qkv_proj", "self_attn.o_proj"] #phi3
    #TARGET_MODULES = ["q_proj", "v_proj"] #phi2/qwen  
    #TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"] # llama 3
    
    LORA_R = 8
    LORA_ALPHA = 16
    LORA_DROPOUT = 0.05
    EPOCHS = 1
    BATCH_SIZE = 2
    LEARNING_RATE = 2e-5
    MAX_OUTPUT_TOKEN = 200 # / 50 pour test uniquement
    TOP_P = 0.9
    TEMPERATURE = 0.7
    TOP_K=40
    
    ''' POUR RAG
    TOP_P =0.85
    TEMPERATURE = 0.2 # plus pertinant en RAG
    TOP_K=40
    
    default 
    TOP_P = 0.9
    TEMPERATURE = 0.7
    TOP_K=40
 
    '''
    MAX_LENGTH = 512

    OUTPUT_DIR = "./models/lora/phi3-lora"
    
    ####### RAG #######
    RAG_MODEL = "./models/all-MiniLM-L6-v2" # pour le embeded
    RAG_ARCHIVE_PATH = "./RAG/archive"    
    INDEX_FAISS = "./models/FAISS/"
    RAG_WEB_ARCHIVE_PATH="./RAG/web_ressources"
    CHUNK_SIZE=1000
    RAG_MIN_SCORE=0.5
    
    SERVER_TIMEOUT=200 # 200 sec par default

Config = BaseConfig