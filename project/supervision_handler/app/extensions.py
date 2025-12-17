from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="threading"
)


@socketio.on("connect")
def on_connect():
    print("🟢 CLIENT CONNECTÉ AU BACKEND")
    socketio.emit("plc_event", {
        "msg": "HELLO FROM BACKEND"
    })