import { io, Socket } from "socket.io-client"

let socket: Socket | null = null

export function initSocket(): void {
  if (socket) return

  socket = io("/", {
    path: "/socket.io",
    transports: ["websocket"]
  })

  socket.on("connect", () => {
    console.log("✅ WS CONNECTÉ", socket!.id)
  })

  socket.on("connect_error", (err) => {
    console.error("❌ WS ERROR", err.message)
  })
}

export function getSocket(): Socket {
  if (!socket) {
    throw new Error("Socket non initialisée. Appelle initSocket() au démarrage.")
  }
  return socket
}
