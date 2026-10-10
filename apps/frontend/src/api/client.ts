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
      // Custom backend error object: { message: string }
      err.message = detail.message
    } else if (typeof detail === 'string') {
      // Plain string detail
      err.message = detail
    } else if (Array.isArray(detail)) {
      // FastAPI / Pydantic 422 validation errors: [{loc, msg, type}, ...]
      const msgs = detail
        .map((e: any) => {
          const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : ''
          const label = field && field !== 'body' ? `${field}: ` : ''
          return `${label}${e.msg}`
        })
        .join(' · ')
      err.message = msgs || 'Validation failed. Please check your inputs.'
    }
    return Promise.reject(err)
  }
)

export default api
