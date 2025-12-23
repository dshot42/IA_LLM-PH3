import axios from 'axios'
import { auth } from './auth'

export const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:5000' // 8080 java be

export const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use((config) => {
  const token = auth.getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})
