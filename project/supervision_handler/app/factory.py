from flask import Flask
from flask_cors import CORS
from app.extensions import db, socketio

def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = \
        "postgresql+psycopg2://postgres:root@localhost:5432/plc"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ✅ CORS GLOBAL (API + OPTIONS auto)
    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:5173"}},
        supports_credentials=True
    )


    # ✅ Extensions
    db.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins="*"  # 🔥 indispensable pour WS
    )

    with app.app_context():
        from . import models
        from .routes import api_bp
        app.register_blueprint(api_bp)

    return app
