import axios from 'axios'
import { auth } from './auth'

export const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8080' // 8080 java be

export const api = axios.create({ baseURL: API_BASE })

export const API_CHAT_IA = (import.meta as any).env?.VITE_API_CHAT_IA || 'http://localhost:5000' // 8080 java be

export const api_ia = axios.create({ baseURL: API_CHAT_IA })

api.interceptors.request.use((config) => {
  const token = auth.getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})
