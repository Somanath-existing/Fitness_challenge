import axios from 'axios'
import { useUserStore } from '../stores/userStore'

// VITE_ prefix required — Vite bakes this in at build time
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:3001'

const api = axios.create({
  baseURL: `${BASE}/api`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10_000,
  withCredentials: true, // Send httpOnly cookies across origins if needed
})

// ── Request interceptor: inject Authorization: Bearer <token> ────────────────
api.interceptors.request.use((config) => {
  const token = useUserStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: surface error details & handle 401 ─────────────────
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      // Clear expired user state if invalid/expired token received
      const currentToken = useUserStore.getState().token
      if (currentToken) {
        useUserStore.getState().clearUser()
      }
    }

    const detail = err.response?.data?.detail
    if (detail?.message) {
      err.message = detail.message
    } else if (typeof detail === 'string') {
      err.message = detail
    }
    return Promise.reject(err)
  }
)

export default api
