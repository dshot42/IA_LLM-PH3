from app.factory import create_app
from app.extensions import socketio
from app.ws import init_socketio

app = create_app()
init_socketio(socketio, app)

@socketio.on("connect")
def on_connect():
    print("🟢 CLIENT CONNECTÉ")
    socketio.emit("ping", {"msg": "pong"})

if __name__ == "__main__":
    print("🚀 Démarrage serveur Flask + REST + SocketIO")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
