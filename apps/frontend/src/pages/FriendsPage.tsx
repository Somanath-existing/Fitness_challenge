import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getFriends,
  sendFriendRequest,
  getFriendRequests,
  respondFriendRequest,
  unfriendUser,
  getLeaderboard,
  getUser,
  getFriendProfile,
  cancelFriendRequest,
} from '../api/endpoints'
import { useUserStore } from '../stores/userStore'
import { formatActivityDate } from '../utils/date'
import { useNavigate } from 'react-router-dom'
import TierBadge from '../components/TierBadge'
import StreakBadge from '../components/StreakBadge'
import type { Tier } from '../types'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts'

const SPORT_EMOJI: Record<string, string> = {
  running: '🏃‍♂️', walking: '🚶‍♀️', cycling: '🚴‍♂️',
  gym: '🏋️‍♂️', swimming: '🏊‍♂️', steps: '👣',
}

const SPORT_COLORS: Record<string, string> = {
  running: '#f97316',
  walking: '#10b981',
  cycling: '#06b6d4',
  gym: '#8b5cf6',
  swimming: '#3b82f6',
  steps: '#ec4899',
}

// ── Friend Activity Dashboard Modal ──────────────────────────────────────────
function FriendProfileModal({
  friend,
  onClose,
  onUnfriend,
  isUnfriending,
}: {
  friend: any
  onClose: () => void
  onUnfriend: () => void
  isUnfriending: boolean
}) {
  const [confirmUnfriend, setConfirmUnfriend] = useState(false)

  const { data: dash, isLoading } = useQuery({
    queryKey: ['friend-profile', friend.user_id],
    queryFn: () => getFriendProfile(friend.user_id),
    staleTime: 30_000,
  })

  const athlete = dash?.user
  const streak = athlete?.streak ?? friend.current_streak ?? 0
  const points = athlete?.total_points ?? friend.total_points ?? 0
  const rank = athlete?.rank
  const tier = (athlete?.tier || 'rookie') as Tier
  const activities = dash?.recent_activities || []
  const weeklyTrend = dash?.weekly_trend || []
  const sportBreakdown = dash?.sport_breakdown || []
  const goalProgress = dash?.goal_progress

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-3 sm:p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-5 sm:p-7 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3.5">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-black text-2xl sm:text-3xl shadow-md shadow-violet-200 shrink-0">
              {friend.first_name?.[0] || '?'}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="font-extrabold text-gray-900 text-xl leading-tight">
                  {friend.first_name} {friend.last_name}
                </h2>
                <TierBadge tier={tier} size="sm" />
                <StreakBadge streak={streak} />
              </div>
              <div className="flex items-center gap-2 mt-1">
                {friend.username && (
                  <span className="text-xs text-violet-600 font-mono font-semibold">@{friend.username}</span>
                )}
                {rank && (
                  <span className="text-xs text-gray-400 font-medium">· Rank #{rank}</span>
                )}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-600 rounded-xl hover:bg-gray-100 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Bio if available */}
        {friend.bio && (
          <div className="bg-gray-50 border border-gray-100 rounded-2xl px-4 py-3">
            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider block mb-0.5">Bio</span>
            <p className="text-xs sm:text-sm text-gray-700 leading-relaxed">{friend.bio}</p>
          </div>
        )}

        {/* Key Activity Stats */}
        <div className="grid grid-cols-3 gap-2.5 sm:gap-3">
          <div className="bg-violet-50 border border-violet-100 rounded-2xl p-3 text-center">
            <div className="text-lg sm:text-2xl font-extrabold text-violet-700 tabular-nums">
              {points.toLocaleString()}
            </div>
            <div className="text-[10px] sm:text-xs text-gray-500 font-semibold mt-0.5">Total Points</div>
          </div>
          <div className="bg-orange-50 border border-orange-100 rounded-2xl p-3 text-center">
            <div className="text-lg sm:text-2xl font-extrabold text-orange-500 tabular-nums">
              {streak}d
            </div>
            <div className="text-[10px] sm:text-xs text-gray-500 font-semibold mt-0.5">Day Streak</div>
          </div>
          <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-3 text-center">
            <div className="text-lg sm:text-2xl font-extrabold text-indigo-700 tabular-nums">
              {rank ? `#${rank}` : '—'}
            </div>
            <div className="text-[10px] sm:text-xs text-gray-500 font-semibold mt-0.5">Global Rank</div>
          </div>
        </div>

        {/* Weekly Goal Progress (if configured) */}
        {goalProgress && goalProgress.target > 0 && (
          <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-xs space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-gray-700 flex items-center gap-1.5">
                <span>🎯</span> Weekly Points Goal
              </span>
              <span className="font-extrabold text-gray-900 tabular-nums">
                {goalProgress.achieved.toLocaleString()} / {goalProgress.target.toLocaleString()} pts ({goalProgress.percentage}%)
              </span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-emerald-500 h-2 rounded-full transition-all"
                style={{ width: `${Math.min(100, goalProgress.percentage)}%` }}
              />
            </div>
          </div>
        )}

        {/* Recent Activity Log */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-extrabold text-gray-900 flex items-center gap-1.5">
              <span>🏃‍♂️</span> Workout Activity Log
            </h3>
            <span className="text-[11px] text-gray-400 font-medium">
              {activities.length} session{activities.length === 1 ? '' : 's'}
            </span>
          </div>

          {isLoading ? (
            <div className="space-y-2 animate-pulse">
              <div className="h-12 bg-gray-100 rounded-2xl" />
              <div className="h-12 bg-gray-100 rounded-2xl" />
              <div className="h-12 bg-gray-100 rounded-2xl" />
            </div>
          ) : activities.length === 0 ? (
            <div className="bg-gray-50 rounded-2xl p-6 text-center text-gray-400 text-xs">
              No workouts logged yet by this athlete.
            </div>
          ) : (
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {activities.map((a) => (
                <div
                  key={a.id}
                  className="flex items-center gap-3 p-3 bg-gray-50/70 hover:bg-violet-50/50 rounded-2xl border border-gray-100 transition-colors"
                >
                  <div className="w-10 h-10 rounded-xl bg-white border border-gray-100 flex items-center justify-center text-xl shrink-0 shadow-xs">
                    {SPORT_EMOJI[a.sport] ?? '🏃'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs sm:text-sm font-bold text-gray-900 truncate">
                      {a.title || `${a.sport.toUpperCase()} session`}
                    </div>
                    <div className="text-[11px] text-gray-400">
                      {a.raw_value} · {formatActivityDate(a.logged_at, athlete?.timezone || 'UTC')}
                    </div>
                  </div>
                  <div className="text-xs font-black text-violet-700 bg-violet-100 px-2.5 py-1 rounded-xl tabular-nums shrink-0">
                    +{a.points_awarded} pts
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Charts: Weekly Points Trend */}
        {weeklyTrend.length > 0 && (
          <div className="bg-gray-50/60 rounded-2xl p-4 border border-gray-100 space-y-2">
            <h4 className="text-xs font-bold text-gray-700">Weekly Points Trend</h4>
            <div className="h-32 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weeklyTrend}>
                  <XAxis dataKey="week" tick={{ fontSize: 9 }} stroke="#9ca3af" />
                  <YAxis tick={{ fontSize: 9 }} stroke="#9ca3af" width={28} />
                  <Tooltip
                    contentStyle={{ fontSize: '11px', borderRadius: '12px', background: '#fff', border: '1px solid #e5e7eb' }}
                    formatter={(v: number) => [`${v.toLocaleString()} pts`, 'Points']}
                  />
                  <Line
                    type="monotone"
                    dataKey="points"
                    stroke="#7c3aed"
                    strokeWidth={2}
                    dot={{ r: 3, fill: '#7c3aed' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Sport Breakdown */}
        {sportBreakdown.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-gray-700">Sport Distribution</h4>
            <div className="flex flex-wrap gap-2">
              {sportBreakdown.map((s) => (
                <div
                  key={s.sport}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium"
                  style={{
                    color: SPORT_COLORS[s.sport] ?? '#6b7280',
                    borderColor: (SPORT_COLORS[s.sport] ?? '#6b7280') + '40',
                    backgroundColor: (SPORT_COLORS[s.sport] ?? '#6b7280') + '10',
                  }}
                >
                  <span>{SPORT_EMOJI[s.sport] ?? '🎯'}</span>
                  <span className="capitalize font-semibold">{s.sport}</span>
                  <span className="opacity-80">({s.percentage}%)</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unfriend Section */}
        <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
          {!confirmUnfriend ? (
            <button
              onClick={() => setConfirmUnfriend(true)}
              className="py-2 px-3 rounded-xl text-xs font-semibold text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition-all"
            >
              Unfriend Athlete
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-rose-600 font-medium">Remove from circle?</span>
              <button
                onClick={onUnfriend}
                disabled={isUnfriending}
                className="px-3 py-1.5 rounded-xl text-xs font-bold text-white bg-rose-600 hover:bg-rose-500 disabled:opacity-60 transition-all shadow-xs"
              >
                {isUnfriending ? 'Removing…' : 'Yes, unfriend'}
              </button>
              <button
                onClick={() => setConfirmUnfriend(false)}
                className="px-2.5 py-1.5 rounded-xl text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 transition-all"
              >
                Cancel
              </button>
            </div>
          )}

          <button
            onClick={onClose}
            className="btn-ghost !py-2 !px-4 !text-xs !rounded-xl"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function FriendsPage() {
  const userId = useUserStore((s) => s.userId)
  const firstName = useUserStore((s) => s.firstName)
  const username = useUserStore((s) => s.username)
  const setUsername = useUserStore((s) => s.setUsername)
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [searchTarget, setSearchTarget] = useState('')
  const [feedback, setFeedback] = useState<{ type: 'ok' | 'err'; msg: string } | null>(null)
  const [viewingFriend, setViewingFriend] = useState<any | null>(null)

  // Load user profile if username is not in store
  const { data: userProfile } = useQuery({
    queryKey: ['user-profile', userId],
    queryFn: async () => {
      if (!userId) return null
      const u = await getUser(userId)
      if (u.username) setUsername(u.username)
      return u
    },
    enabled: !!userId && !username,
    staleTime: Infinity,
  })

  const currentUsername = username || userProfile?.username

  // 1. Accepted friends
  const { data: friendsData, isLoading: friendsLoading } = useQuery({
    queryKey: ['friends', userId],
    queryFn: () => getFriends(),
    enabled: !!userId,
    staleTime: 10_000,
  })

  // 2. Pending requests
  const { data: requestsData } = useQuery({
    queryKey: ['friend-requests', userId],
    queryFn: () => getFriendRequests(),
    enabled: !!userId,
    staleTime: 5_000,
    refetchInterval: 10_000,
  })

  // 3. Friends leaderboard
  const { data: friendLb } = useQuery({
    queryKey: ['leaderboard', 'friends', userId],
    queryFn: () => getLeaderboard({ scope: 'friends', user_id: userId ?? undefined, limit: 50 }),
    enabled: !!userId,
    staleTime: 10_000,
  })

  // Send request mutation
  const sendMutation = useMutation({
    mutationFn: () => sendFriendRequest(searchTarget.trim()),
    onSuccess: (data) => {
      setFeedback({ type: 'ok', msg: data.message || 'Friend request sent!' })
      setSearchTarget('')
      qc.invalidateQueries({ queryKey: ['friend-requests', userId] })
    },
    onError: (err: Error) => setFeedback({ type: 'err', msg: err.message }),
  })

  // Respond to request mutation
  const respondMutation = useMutation({
    mutationFn: ({ friendshipId, action }: { friendshipId: string; action: 'accept' | 'decline' }) =>
      respondFriendRequest(friendshipId, action),
    onSuccess: (_, variables) => {
      setFeedback({
        type: 'ok',
        msg: variables.action === 'accept' ? 'Friend request accepted! You are now friends.' : 'Friend request declined.',
      })
      qc.invalidateQueries({ queryKey: ['friends', userId] })
      qc.invalidateQueries({ queryKey: ['friend-requests', userId] })
      qc.invalidateQueries({ queryKey: ['leaderboard', 'friends', userId] })
    },
    onError: (err: Error) => setFeedback({ type: 'err', msg: err.message }),
  })

  // Cancel outgoing request mutation
  const cancelOutgoingMutation = useMutation({
    mutationFn: (friendshipId: string) => cancelFriendRequest({ friendshipId }),
    onSuccess: () => {
      setFeedback({ type: 'ok', msg: 'Friend request cancelled.' })
      qc.invalidateQueries({ queryKey: ['friend-requests', userId] })
    },
    onError: (err: Error) => setFeedback({ type: 'err', msg: err.message }),
  })

  // Unfriend mutation
  const unfriendMutation = useMutation({
    mutationFn: ({ friendshipId }: { friendshipId: string }) => unfriendUser(friendshipId),
    onSuccess: () => {
      setFeedback({ type: 'ok', msg: `${viewingFriend?.first_name} has been removed from your circle.` })
      setViewingFriend(null)
      qc.invalidateQueries({ queryKey: ['friends', userId] })
      qc.invalidateQueries({ queryKey: ['leaderboard', 'friends', userId] })
    },
    onError: (err: Error) => setFeedback({ type: 'err', msg: err.message }),
  })

  if (!userId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-4 text-center">
        <div className="w-20 h-20 rounded-3xl bg-violet-100 flex items-center justify-center text-4xl shadow-sm text-violet-600">
          👥
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900">Connect with Friends</h2>
          <p className="text-sm text-gray-500 max-w-sm mt-1">
            Sign in or register an account to send friend requests, see shared rankings, and challenge your peers.
          </p>
        </div>
        <button onClick={() => navigate('/register')} className="btn-primary">
          Sign In / Register
        </button>
      </div>
    )
  }

  const incomingRequests = requestsData?.incoming || []
  const outgoingRequests = requestsData?.outgoing || []

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      {/* Friend Profile Modal */}
      {viewingFriend && (
        <FriendProfileModal
          friend={viewingFriend}
          onClose={() => setViewingFriend(null)}
          onUnfriend={() => unfriendMutation.mutate({ friendshipId: viewingFriend.friendship_id })}
          isUnfriending={unfriendMutation.isPending}
        />
      )}

      {/* ── Page Header ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold text-violet-600 uppercase tracking-widest mb-0.5">Social & Peers</p>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Friends</h1>
          <p className="text-sm text-gray-500 mt-0.5">Connect, compete, and track milestones together</p>
        </div>
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white text-xl shadow-md shadow-violet-200">
          👥
        </div>
      </div>

      {/* ── Your Username Banner ──────────────────────────────── */}
      <div className="bg-gradient-to-r from-violet-600 to-purple-600 rounded-3xl p-5 text-white shadow-lg shadow-violet-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-semibold text-violet-200 uppercase tracking-wider block">Your Athlete Handle</span>
          <span className="text-2xl font-black font-mono tracking-tight block mt-0.5">
            {currentUsername ? `@${currentUsername}` : `@${firstName?.toLowerCase() || 'athlete'}`}
          </span>
          <span className="text-xs text-violet-100/90 block mt-1">
            Share this with friends so they can add you to their circle.
          </span>
        </div>
        {currentUsername && (
          <button
            onClick={() => {
              navigator.clipboard.writeText(currentUsername)
              setFeedback({ type: 'ok', msg: `Copied @${currentUsername} to clipboard!` })
            }}
            className="self-start sm:self-auto bg-white/20 hover:bg-white/30 backdrop-blur-md text-white border border-white/30 px-4 py-2 rounded-2xl transition-all font-semibold text-xs shrink-0 flex items-center gap-1.5 active:scale-95"
          >
            <span>📋</span> Copy Handle
          </button>
        )}
      </div>

      {/* ── Feedback Notification ─────────────────────────────── */}
      {feedback && (
        <div
          className={`text-sm rounded-2xl p-4 flex items-center gap-3 shadow-sm border ${
            feedback.type === 'ok'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          <span className="text-xl">{feedback.type === 'ok' ? '✅' : '⚠️'}</span>
          <span className="font-medium flex-1">{feedback.msg}</span>
          <button onClick={() => setFeedback(null)} className="text-gray-400 hover:text-gray-600 text-sm font-bold">✕</button>
        </div>
      )}

      {/* ── Incoming Friend Requests ──────────────────────────── */}
      {incomingRequests.length > 0 && (
        <div className="bg-white border-2 border-violet-200 rounded-3xl p-5 space-y-3 shadow-md shadow-violet-100">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-gray-900 flex items-center gap-2 text-base">
              <span>📬 Incoming Requests</span>
              <span className="bg-violet-600 text-white text-xs px-2.5 py-0.5 rounded-full font-bold">
                {incomingRequests.length} new
              </span>
            </h3>
          </div>
          <p className="text-xs text-gray-500">
            Accept invitations to compete together on the exclusive Friends Leaderboard!
          </p>
          <div className="space-y-2 mt-2">
            {incomingRequests.map((req: any) => (
              <div
                key={req.friendship_id}
                className="flex items-center justify-between gap-3 bg-gray-50/80 border border-gray-100 rounded-2xl p-3.5 hover:bg-violet-50/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow-sm">
                    {req.first_name?.[0] || '?'}
                  </div>
                  <div>
                    <div className="text-sm font-bold text-gray-900">{req.first_name} {req.last_name}</div>
                    {req.username && <div className="text-xs text-violet-600 font-mono font-medium">@{req.username}</div>}
                    <div className="text-xs text-gray-400 mt-0.5">{req.total_points} pts · {req.current_streak}d streak</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => respondMutation.mutate({ friendshipId: req.friendship_id, action: 'accept' })}
                    disabled={respondMutation.isPending}
                    className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => respondMutation.mutate({ friendshipId: req.friendship_id, action: 'decline' })}
                    disabled={respondMutation.isPending}
                    className="bg-gray-100 hover:bg-gray-200 disabled:opacity-50 text-gray-600 px-3 py-2 rounded-xl text-xs font-semibold transition-all"
                  >
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Add Friend by Username ────────────────────────────── */}
      <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm">
        <h3 className="font-bold text-gray-900 mb-1">Add a Friend</h3>
        <p className="text-xs text-gray-500 mb-4">
          Enter your friend's <span className="text-violet-600 font-semibold">handle</span> (e.g.{' '}
          <span className="font-mono text-gray-700 bg-gray-100 px-1.5 py-0.5 rounded">alice_chen</span>).
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (searchTarget.trim()) {
              setFeedback(null)
              sendMutation.mutate()
            }
          }}
          className="flex gap-2"
        >
          <div className="relative flex-1">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-mono text-sm">@</span>
            <input
              id="friend-search-input"
              className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-2xl pl-8 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 focus:bg-white transition-all font-mono placeholder:text-gray-400"
              placeholder="username"
              value={searchTarget.replace(/^@/, '')}
              onChange={(e) => { setSearchTarget(e.target.value); setFeedback(null) }}
            />
          </div>
          <button
            type="submit"
            id="friend-send-btn"
            disabled={sendMutation.isPending || !searchTarget.trim()}
            className="btn-primary !rounded-2xl !py-3 !px-5 text-sm"
          >
            {sendMutation.isPending ? 'Sending…' : 'Send Invite'}
          </button>
        </form>
      </div>

      {/* ── Outgoing Pending Requests ──────────────────────────── */}
      {outgoingRequests.length > 0 && (
        <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm space-y-3">
          <h3 className="font-bold text-gray-800 text-sm">
            Pending Outgoing Requests ({outgoingRequests.length})
          </h3>
          <div className="space-y-2">
            {outgoingRequests.map((req: any) => (
              <div
                key={req.friendship_id}
                className="flex items-center justify-between py-2.5 px-3 bg-gray-50 rounded-2xl"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-800">{req.first_name} {req.last_name}</span>
                  {req.username && <span className="text-xs text-violet-600 font-mono">@{req.username}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-amber-50 text-amber-700 px-3 py-1 rounded-full font-medium border border-amber-200">
                    Waiting for response
                  </span>
                  <button
                    onClick={() => cancelOutgoingMutation.mutate(req.friendship_id)}
                    disabled={cancelOutgoingMutation.isPending && cancelOutgoingMutation.variables === req.friendship_id}
                    className="text-xs text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-2.5 py-1 rounded-xl font-semibold transition-colors border border-rose-200 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Friends Leaderboard ─────────────────────────────────── */}
      {friendLb && friendLb.data.length > 0 && (
        <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs font-semibold text-violet-600 uppercase tracking-widest">Mini League</p>
              <h3 className="font-bold text-gray-900 text-lg">Friends Leaderboard</h3>
            </div>
            <span className="text-xs font-semibold bg-violet-50 text-violet-700 px-3 py-1 rounded-full">
              {friendLb.data.length} athletes
            </span>
          </div>
          <div className="space-y-2">
            {friendLb.data.map((entry) => {
              const isMe = entry.user_id === userId
              return (
                <div
                  key={entry.user_id}
                  className={`flex items-center gap-3.5 rounded-2xl px-4 py-3 transition-colors ${
                    isMe
                      ? 'bg-violet-50 border border-violet-200'
                      : 'bg-gray-50/70 hover:bg-gray-50 border border-transparent'
                  }`}
                >
                  <span className="text-sm font-bold w-6 text-center text-gray-700">
                    {entry.rank <= 3 ? ['🥇', '🥈', '🥉'][entry.rank - 1] : `#${entry.rank}`}
                  </span>
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-violet-400 to-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow-sm">
                    {entry.first_name?.[0] || 'A'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-gray-900 flex items-center gap-1.5 truncate">
                      <span>{entry.first_name}</span>
                      {entry.username && <span className="text-xs text-gray-400 font-mono font-normal">@{entry.username}</span>}
                      {isMe && <span className="text-violet-600 text-xs font-semibold">(you)</span>}
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <TierBadge tier={entry.tier as Tier} size="sm" />
                      <StreakBadge streak={entry.current_streak} />
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-base font-extrabold text-gray-900 tabular-nums">
                      {entry.total_points.toLocaleString()}
                    </span>
                    <span className="text-gray-400 font-medium text-xs ml-1">pts</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Accepted Friends List ──────────────────────────────── */}
      <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-gray-900 text-lg">
            Your Circle
            {friendsData && (
              <span className="text-gray-400 font-normal text-sm ml-2">({friendsData.count})</span>
            )}
          </h3>
        </div>

        {friendsLoading && (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-14 bg-gray-50 rounded-2xl animate-pulse" />
            ))}
          </div>
        )}

        {!friendsLoading && (!friendsData?.friends || friendsData.friends.length === 0) && (
          <div className="text-gray-400 text-sm text-center py-8">
            No friends added yet. Share your handle or send a request above to get started!
          </div>
        )}

        <div className="space-y-2.5">
          {friendsData?.friends?.map((f: any) => (
            <div
              key={f.user_id}
              className="flex items-center gap-3.5 p-3.5 bg-gray-50/60 hover:bg-violet-50/30 rounded-2xl transition-all border border-gray-100"
            >
              {/* Avatar — clickable to view profile */}
              <button
                onClick={() => setViewingFriend(f)}
                className="w-10 h-10 rounded-2xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center text-white font-bold text-sm shadow-sm hover:scale-105 transition-transform shrink-0"
              >
                {f.first_name[0]}
              </button>

              <div className="flex-1 min-w-0">
                <button
                  onClick={() => setViewingFriend(f)}
                  className="text-sm font-bold text-gray-900 hover:text-violet-700 transition-colors truncate block text-left"
                >
                  {f.first_name} {f.last_name}
                </button>
                {f.username && <div className="text-xs text-violet-600 font-mono">@{f.username}</div>}
              </div>

              <div className="hidden sm:block text-right shrink-0">
                <div className="text-sm font-bold text-gray-900 tabular-nums">{f.total_points.toLocaleString()} pts</div>
                {f.current_streak > 0 && (
                  <div className="text-xs text-orange-500 font-semibold">🔥 {f.current_streak}d</div>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => navigate(`/challenges?friendId=${f.user_id}&friendName=${encodeURIComponent(f.first_name)}`)}
                  title="Challenge"
                  className="bg-violet-50 hover:bg-violet-600 text-violet-700 hover:text-white border border-violet-200 px-3 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1 shadow-sm"
                >
                  🎯 Challenge
                </button>
                <button
                  onClick={() => setViewingFriend(f)}
                  title="View profile"
                  className="bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-2 rounded-xl text-xs font-semibold transition-all"
                >
                  View
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
