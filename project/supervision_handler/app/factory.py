from flask import Flask
from flask_cors import CORS
from supervision_handler.app.extensions import db, socketio

def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = \
        "postgresql+psycopg2://postgres:root@localhost:5432/plc"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(
        app,
        resources={r"/*": {"origins": "http://localhost:5173"}},
        supports_credentials=True
    )

    db.init_app(app)
    socketio.init_app(app)

    with app.app_context():
        from . import models
        from .routes import api_bp
        from .route_chat_ia import ia_api

        app.register_blueprint(api_bp)
        app.register_blueprint(ia_api)

    return app
