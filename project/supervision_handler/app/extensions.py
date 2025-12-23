from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="threading"
)

import ia.model as model_utils

def load_models():
    global tokenizer, model
    print(" --- Loading Models...")
    tokenizer = model_utils.load_tokenizer()
    model = model_utils.load_standard_model()
    return tokenizer, model

def load_models_gguf():
    return None,  model_utils.llm()

tokenizer, model = load_models_gguf() # load_models()