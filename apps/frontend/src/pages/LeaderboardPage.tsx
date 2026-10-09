import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLeaderboard, sendFriendRequest, getFriends, getFriendRequests, cancelFriendRequest } from '../api/endpoints'
import { useUserStore } from '../stores/userStore'
import { useLeaderboardSocket } from '../hooks/useLeaderboardSocket'
import TierBadge from '../components/TierBadge'
import StreakBadge from '../components/StreakBadge'
import type { Tier } from '../types'

const TIER_FILTERS: Array<{ label: string; value: string }> = [
  { label: 'All', value: '' },
  { label: '🌱 Rookie', value: 'rookie' },
  { label: '⚡ Active', value: 'active' },
  { label: '🏃 Athlete', value: 'athlete' },
  { label: '🥈 Competitor', value: 'competitor' },
  { label: '🏆 Elite', value: 'elite' },
]

const RANK_COLORS = ['from-amber-400 to-yellow-500', 'from-gray-300 to-gray-400', 'from-orange-400 to-amber-600']

export default function LeaderboardPage() {
  const userId = useUserStore((s) => s.userId)
  const [scope, setScope] = useState<'global' | 'friends'>('global')
  const [tierFilter, setTierFilter] = useState('')

  useLeaderboardSocket()

  const qc = useQueryClient()
  const [sentTo, setSentTo] = useState<Set<string>>(new Set())
  const [actionMsg, setActionMsg] = useState<{ id: string; text: string; isError?: boolean } | null>(null)

  const { data: friendsData } = useQuery({
    queryKey: ['friends', userId],
    queryFn: () => getFriends(),
    enabled: !!userId,
  })

  const { data: requestsData } = useQuery({
    queryKey: ['friend-requests', userId],
    queryFn: () => getFriendRequests(),
    enabled: !!userId,
    refetchInterval: 15_000,
  })

  const friendUserIds = new Set((friendsData?.friends || []).map((f: any) => f.user_id))
  const outgoingUserIds = new Set((requestsData?.outgoing || []).map((r: any) => r.user_id))

  const addFriendMutation = useMutation({
    mutationFn: (target: string) => sendFriendRequest(target),
    onSuccess: (_, target) => {
      const matched = data?.data.find((e) => e.username === target || e.user_id === target)
      const targetId = matched ? matched.user_id : target
      setSentTo((prev) => new Set([...prev, targetId]))
      setActionMsg({ id: targetId, text: 'Sent!' })
      qc.invalidateQueries({ queryKey: ['friends', userId] })
      qc.invalidateQueries({ queryKey: ['friend-requests', userId] })
    },
    onError: (err: any, target) => {
      const msg = err.response?.data?.detail?.message || err.message || 'Failed'
      const matched = data?.data.find((e) => e.username === target || e.user_id === target)
      const targetId = matched ? matched.user_id : target
      setActionMsg({ id: targetId, text: typeof msg === 'string' ? msg : 'Error', isError: true })
    },
  })

  const cancelFriendMutation = useMutation({
    mutationFn: (targetId: string) => cancelFriendRequest({ targetId }),
    onSuccess: (_, targetId) => {
      setSentTo((prev) => {
        const next = new Set(prev)
        next.delete(targetId)
        return next
      })
      setActionMsg({ id: targetId, text: 'Cancelled' })
      qc.invalidateQueries({ queryKey: ['friend-requests', userId] })
      qc.invalidateQueries({ queryKey: ['friends', userId] })
    },
    onError: (err: any, targetId) => {
      setActionMsg({ id: targetId, text: 'Failed to cancel', isError: true })
    },
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['leaderboard', scope, tierFilter, userId],
    queryFn: () =>
      getLeaderboard({
        limit: 100,
        scope,
        tier: tierFilter || undefined,
        user_id: userId ?? undefined,
      }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <p className="text-xs font-semibold text-violet-500 uppercase tracking-widest mb-1">Rankings</p>
        <h1 className="text-2xl font-extrabold text-gray-900">Leaderboard</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          🔴 Live · {data?.total ?? '—'} athletes competing
        </p>
      </div>

      {/* Scope toggle */}
      <div className="flex gap-2 mb-5 p-1 bg-white rounded-2xl shadow-sm border border-gray-100 w-fit">
        {(['global', 'friends'] as const).map((s) => (
          <button
            key={s}
            id={`scope-${s}`}
            onClick={() => setScope(s)}
            disabled={s === 'friends' && !userId}
            className={`px-5 py-1.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
              scope === s
                ? 'bg-violet-600 text-white shadow-md shadow-violet-200'
                : 'text-gray-500 hover:text-gray-800'
            } disabled:opacity-40`}
          >
            {s === 'global' ? '🌍 Global' : '👥 Friends'}
          </button>
        ))}
      </div>

      {/* Tier filter chips */}
      <div className="flex gap-2 flex-wrap mb-5">
        {TIER_FILTERS.map((f) => (
          <button
            key={f.value}
            id={`tier-filter-${f.value || 'all'}`}
            onClick={() => setTierFilter(f.value)}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-all duration-200 border ${
              tierFilter === f.value
                ? 'bg-violet-600 text-white border-violet-600 shadow-sm shadow-violet-200'
                : 'bg-white text-gray-500 border-gray-200 hover:border-violet-300 hover:text-violet-600'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Top 3 podium */}
      {!isLoading && !error && data && data.data.length >= 3 && (
        <div className="grid grid-cols-3 gap-3 mb-5">
          {[1, 0, 2].map((rank, podiumIdx) => {
            const entry = data.data[rank]
            if (!entry) return null
            const isMe = entry.user_id === userId
            const heights = ['h-24', 'h-32', 'h-20']
            const medals = ['🥈', '🥇', '🥉']
            return (
              <div key={entry.user_id} className={`flex flex-col items-center justify-end`}>
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-400 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow mb-1">
                  {entry.first_name[0]}
                </div>
                <p className="text-xs font-semibold text-gray-700 truncate max-w-full px-1">{entry.first_name}</p>
                <p className="text-xs text-gray-400">{entry.total_points.toLocaleString()} pts</p>
                <div className={`${heights[podiumIdx]} w-full mt-2 rounded-t-2xl bg-gradient-to-b ${RANK_COLORS[rank]} flex items-start justify-center pt-2 shadow-inner`}>
                  <span className="text-xl">{medals[podiumIdx]}</span>
                </div>
                {isMe && <div className="w-full h-1 bg-violet-500 rounded-b-sm mt-0" />}
              </div>
            )
          })}
        </div>
      )}

      {/* Full list */}
      {isLoading && (
        <div className="space-y-3">
          {[0, 1, 2, 3, 4].map(i => (
            <div key={i} className="fit-card animate-pulse flex gap-4 items-center">
              <div className="w-8 h-8 rounded-full bg-gray-100" />
              <div className="flex-1 space-y-2">
                <div className="h-3 bg-gray-100 rounded w-1/3" />
                <div className="h-2 bg-gray-100 rounded w-1/4" />
              </div>
              <div className="h-5 w-16 bg-gray-100 rounded" />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="fit-card text-center py-8 text-red-500 text-sm">
          Failed to load leaderboard
        </div>
      )}

      {data && (
        <div className="space-y-2.5">
          {data.data.map((entry) => {
            const isMe = entry.user_id === userId
            return (
              <div
                key={entry.user_id}
                id={`leaderboard-entry-${entry.user_id}`}
                className={`flex items-center gap-3 rounded-2xl px-4 py-3 transition-all duration-200 border ${
                  isMe
                    ? 'bg-violet-50 border-violet-200 shadow-sm shadow-violet-100'
                    : 'bg-white border-gray-100 hover:border-violet-200 shadow-sm'
                }`}
              >
                {/* Rank */}
                <div className="w-8 text-center shrink-0">
                  {entry.rank <= 3 ? (
                    <span className="text-xl">{['🥇', '🥈', '🥉'][entry.rank - 1]}</span>
                  ) : (
                    <span className="text-gray-400 text-sm font-mono font-semibold">#{entry.rank}</span>
                  )}
                </div>

                {/* Avatar */}
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white font-bold text-sm shrink-0 shadow-sm ${
                  isMe ? 'bg-gradient-to-br from-violet-500 to-purple-700' : 'bg-gradient-to-br from-gray-300 to-gray-400'
                }`}>
                  {entry.first_name[0]}
                </div>

                {/* Name + tier */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-semibold text-gray-900 text-sm truncate">
                      {entry.first_name}
                      {isMe && <span className="text-violet-500 text-xs ml-1">(you)</span>}
                    </span>
                    {entry.username && (
                      <span className="text-gray-400 text-xs">@{entry.username}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <TierBadge tier={entry.tier as Tier} size="sm" />
                    <StreakBadge streak={entry.current_streak} />
                  </div>
                </div>

                {/* Rank delta */}
                {entry.rank_delta !== 0 && (
                  <div className={`text-xs font-semibold ${entry.rank_delta > 0 ? 'text-emerald-500' : 'text-red-400'}`}>
                    {entry.rank_delta > 0 ? `↑${entry.rank_delta}` : `↓${Math.abs(entry.rank_delta)}`}
                  </div>
                )}

                {/* Points */}
                <div className="text-right shrink-0">
                  <div className="font-bold text-gray-900 tabular-nums text-sm">
                    {entry.total_points.toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-400">pts</div>
                </div>

                {/* Add Friend button if not me and logged in */}
                {userId && !isMe && (
                  <div className="shrink-0 ml-1">
                    {friendUserIds.has(entry.user_id) ? (
                      <span className="text-[11px] font-semibold text-violet-600 bg-violet-50 px-2.5 py-1 rounded-xl border border-violet-100 flex items-center gap-1">
                        <span>✓</span> Friend
                      </span>
                    ) : sentTo.has(entry.user_id) || outgoingUserIds.has(entry.user_id) ? (
                      <div className="flex items-center gap-1">
                        <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-100 flex items-center gap-1">
                          <span>✓</span> Sent
                        </span>
                        <button
                          id={`cancel-request-${entry.user_id}`}
                          onClick={() => cancelFriendMutation.mutate(entry.user_id)}
                          disabled={cancelFriendMutation.isPending && cancelFriendMutation.variables === entry.user_id}
                          title="Cancel sent friend request"
                          className="text-gray-400 hover:text-rose-600 hover:bg-rose-50 px-1.5 py-0.5 rounded-lg text-xs font-semibold transition-colors"
                        >
                          {cancelFriendMutation.isPending && cancelFriendMutation.variables === entry.user_id ? '…' : 'Cancel'}
                        </button>
                      </div>
                    ) : actionMsg?.id === entry.user_id && actionMsg.isError ? (
                      <span className="text-[11px] font-semibold text-rose-600 bg-rose-50 px-2 py-1 rounded-xl border border-rose-100" title={actionMsg.text}>
                        {actionMsg.text}
                      </span>
                    ) : (
                      <button
                        id={`add-friend-${entry.user_id}`}
                        onClick={() => addFriendMutation.mutate(entry.username || entry.user_id)}
                        disabled={addFriendMutation.isPending && addFriendMutation.variables === (entry.username || entry.user_id)}
                        className="px-2.5 py-1 rounded-xl text-xs font-semibold bg-violet-50 text-violet-700 hover:bg-violet-600 hover:text-white transition-all duration-150 border border-violet-200 shadow-xs disabled:opacity-50 flex items-center gap-1"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                        </svg>
                        <span>Add</span>
                      </button>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {data.data.length === 0 && (
            <div className="fit-card text-center py-12 text-gray-400 text-sm">
              No athletes found for this filter.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
