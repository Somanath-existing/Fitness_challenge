import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { WsMessage } from '../types'

const WS_BASE = import.meta.env.VITE_API_URL?.replace(/^http/, 'ws') || 'ws://localhost:3001'

export function useLeaderboardSocket() {
  const qc = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let retryDelay = 1000

    const connect = () => {
      try {
        const ws = new WebSocket(`${WS_BASE}/ws`)
        wsRef.current = ws

        ws.onopen = () => {
          retryDelay = 1000 // Reset backoff on successful connect
        }

        ws.onmessage = (event: MessageEvent) => {
          try {
            const msg: WsMessage = JSON.parse(event.data)
            if (msg.event === 'leaderboard:updated') {
              // Invalidate → TanStack Query refetches in background
              qc.invalidateQueries({ queryKey: ['leaderboard'] })
            }
          } catch {
            // Malformed message — ignore
          }
        }

        ws.onerror = () => {
          ws.close()
        }

        ws.onclose = () => {
          wsRef.current = null
          // Exponential backoff reconnect (max 30s)
          retryDelay = Math.min(retryDelay * 2, 30_000)
          reconnectTimerRef.current = setTimeout(connect, retryDelay)
        }
      } catch {
        // WebSocket constructor can throw in some environments
        reconnectTimerRef.current = setTimeout(connect, retryDelay)
      }
    }

    connect()

    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      const current = wsRef.current
      if (current) {
        if (current.readyState === WebSocket.OPEN) {
          current.close()
        } else if (current.readyState === WebSocket.CONNECTING) {
          current.onopen = () => { current.close() }
        }
      }
    }
  }, [qc])
}
