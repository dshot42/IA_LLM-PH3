import { io, Socket } from 'socket.io-client'
import { API_BASE } from './api'
import { auth } from './auth'

let socket: Socket | null = null

export function getSocket(): Socket {
  if (socket) return socket
  socket = io(API_BASE, {
    transports: ['websocket', 'polling'],
    auth: { token: auth.getToken() }
  })
  return socket
}

export function closeSocket() {
  socket?.close()
  socket = null
}
