import os
import os.path as op


class BaseConfig(object):
    BASEDIR = op.abspath(op.dirname(__file__))
    PROJECT_ROOT = BASEDIR
    
    RESSOURCES_DIR = op.join(PROJECT_ROOT, "ressources")

    DEVICE_MAP="cpu" # cuda , xpu
    #MODEL_NAME = op.join(RESSOURCES_DIR, "models/phi3") # CPU "models/phi2-mini| Phi-3-mini-128k-instruct | Llama-3.1-8B"
    #TARGET_MODULES = ["self_attn.qkv_proj", "self_attn.o_proj"] #phi3
    #TARGET_MODULES = ["q_proj", "v_proj"] #phi2/qwen  
    #TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"] # llama 3
    
    MODEL_NAME = op.join(RESSOURCES_DIR, "models/mistral/mistral-7b-v0.1.Q5_K_M.gguf") # version gguf
    TARGET_MODULES = ["self_attn.qkv_proj", "self_attn.o_proj"] #phi3
    
    LORA_R = 8
    LORA_ALPHA = 16
    LORA_DROPOUT = 0.05
    EPOCHS = 1
    BATCH_SIZE = 2
    LEARNING_RATE = 2e-5
    MAX_OUTPUT_TOKEN = 300 # / 200  pour test uniquement

    TEMPERATURE = 0.0 # plus pertinant en RAG
    TOP_K = 1
    TOP_P = 0
    
    ''' POUR RAG
    TEMPERATURE = 0.0 # plus pertinant en RAG
    TOP_K = 1
    TOP_P = 0
    
    
    default 
    TOP_P = 0.9
    TEMPERATURE = 0.7
    TOP_K=40
 
    '''
    MAX_LENGTH =512 # 512 

    OUTPUT_DIR =  op.join(RESSOURCES_DIR,"models/lora/phi3-lora")
    
    ####### RAG #######
    RAG_MODEL = op.join(RESSOURCES_DIR,"models/bge" ) # pour le embeded  "./models/bge" "BAAI/bge-base-en-v1.5"
    RAG_ARCHIVE_PATH = op.join(RESSOURCES_DIR, "RAG/archive/" )   
    RAG_WEB_ARCHIVE_PATH= op.join(RESSOURCES_DIR,"RAG/web_ressources") 
    INDEX_FAISS = op.join(RESSOURCES_DIR,"models/FAISS/") 

    CHUNK_SIZE=400 # taille des chunks de doc pour FAISS 
    RAG_MIN_SCORE=0.8 #seuil min de pertinence pour repondre en RAG 0.7 
    nb_chunks_to_use=1000
    #on prend en compte les X meilleurs chunks  
    #et on check si > RAG_MIN_SCORE pour la reponse RAG avant prompt a mon model LLM, 5 à 10 pour gros LLM 7B
    
    SERVER_TIMEOUT=200 # 200 sec par default
    
    #### WORKFLOW ####
    folder_workflow = op.join(RESSOURCES_DIR,"industrie/ligne_PLC-advanced/workflow") 
    rag_folder_workflow =  op.join(RESSOURCES_DIR,"industrie/ligne_PLC-advanced/faiss")
    rapport_llm_export =  op.join(RESSOURCES_DIR,"rapport_llm_export")

Config = BaseConfig