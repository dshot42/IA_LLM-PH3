from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO(
    async_mode="threading",
    cors_allowed_origins="*"
)

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = \
        "postgresql+psycopg2://user:password@localhost:5432/plc"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    socketio.init_app(app)

    with app.app_context():
       from . import models


    return app

# ✅ On crée l’app ici
app = create_app()