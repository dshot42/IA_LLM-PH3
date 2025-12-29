import os
import os.path as op


class BaseConfig(object):
    BASEDIR = op.abspath(op.dirname(__file__))
    PROJECT_ROOT = BASEDIR
    
    RESSOURCES_DIR = op.join(PROJECT_ROOT, "ressources")

    DEVICE_MAP="cpu" # cuda , xpu
    #MODEL_NAME = op.join(RESSOURCES_DIR, "models/phi3") # meilleur version instruct ! ! !
    #TARGET_MODULES = ["self_attn.qkv_proj", "self_attn.o_proj"] #phi3
    
   
    MODEL_NAME = op.join(RESSOURCES_DIR, "models/qwen2-7b/qwen2-7b-instruct-q5_k_m.gguf") #  meilleure version gguf
    
    #MODEL_NAME = op.join(RESSOURCES_DIR, "models/qwen3-8b-q5/qwen3-8b-q5_k_m.gguf")
    
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
    WORKFLOW_ARCHIVE = op.join(RESSOURCES_DIR, "RAG/workflow/" )   

    RAG_WEB_ARCHIVE_PATH= op.join(RESSOURCES_DIR,"RAG/web_ressources") 
    INDEX_FAISS = op.join(RESSOURCES_DIR,"models/FAISS/") 

    CHUNK_SIZE=1000 # taille des chunks de doc pour FAISS 
    RAG_MIN_SCORE=0.75 #seuil min de pertinence pour repondre en RAG 0.7 
    RAG_MIN_SCORE_WORKFLOW=0.6
    nb_chunks_to_use=1000
    #on prend en compte les X meilleurs chunks  
    #et on check si > RAG_MIN_SCORE pour la reponse RAG avant prompt a mon model LLM, 5 à 10 pour gros LLM 7B
    
    SERVER_TIMEOUT=200 # 200 sec par default
    
    #### WORKFLOW ####
    folder_workflow = op.join(RESSOURCES_DIR,"workflow") 
    rapport_llm_export =  op.join(RESSOURCES_DIR,"rapport_llm_export")
    
    sql_database =  r"C:\Users\come_\Desktop\ia-llm\phi3\project\ressources\schema_db.sql"

Config = BaseConfig