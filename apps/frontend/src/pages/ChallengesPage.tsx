import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getDailyChallenge, getChallenges, createChallenge, respondChallenge, getFriends, deleteChallenge } from '../api/endpoints'
import { useUserStore } from '../stores/userStore'
import { useNavigate, useSearchParams } from 'react-router-dom'
import type { UserChallenge } from '../types'

const DIFFICULTY_CONFIG = {
  easy: { label: 'Easy', classes: 'bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold' },
  medium: { label: 'Medium', classes: 'bg-amber-50 text-amber-700 border-amber-200 font-semibold' },
  hard: { label: 'Hard', classes: 'bg-rose-50 text-rose-700 border-rose-200 font-semibold' },
}

const SPORT_EMOJI: Record<string, string> = {
  running: '🏃‍♂️', walking: '🚶‍♀️', cycling: '🚴‍♂️',
  gym: '🏋️‍♂️', swimming: '🏊‍♂️', steps: '👣',
}

function getMetricUnit(metricType?: string): string {
  if (metricType === 'distance_km') return 'km'
  if (metricType === 'count') return 'steps'
  if (metricType === 'duration_minsec') return 'min'
  if (metricType === 'points') return 'pts'
  return ''
}

function DailyCard({ userId }: { userId: string }) {
  const navigate = useNavigate()
  const { data, isLoading, error } = useQuery({
    queryKey: ['daily-challenge', userId],
    queryFn: () => getDailyChallenge(userId),
    staleTime: 30_000,
    retry: 1,
  })

  if (isLoading) {
    return (
      <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm animate-pulse">
        <div className="h-4 bg-gray-100 rounded-full w-1/3 mb-3" />
        <div className="h-6 bg-gray-100 rounded-full w-2/3 mb-2" />
        <div className="h-4 bg-gray-100 rounded-full w-full" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm">
        <p className="text-gray-400 text-sm">Daily challenge unavailable right now.</p>
      </div>
    )
  }

  const diff = DIFFICULTY_CONFIG[data.difficulty as keyof typeof DIFFICULTY_CONFIG] ?? DIFFICULTY_CONFIG.medium
  const target = typeof data.metric?.target === 'number' ? data.metric.target : parseFloat(String(data.metric?.target)) || 1
  const metricLabel = getMetricUnit(data.metric?.type)
  const targetDisplay = `${target} ${metricLabel}`

  const myProgress: number = (data as any).my_progress ?? 0
  const myStatus: string = (data as any).my_status ?? 'accepted'
  const progressPct = Math.min(100, Math.round((myProgress / target) * 100))
  const isCompleted = myStatus === 'completed' || myProgress >= target

  return (
    <div className={`bg-white rounded-3xl p-6 sm:p-7 shadow-sm border transition-all ${isCompleted
        ? 'border-emerald-200 bg-gradient-to-br from-white via-emerald-50/20 to-emerald-50/40 shadow-emerald-100'
        : 'border-gray-100 hover:border-violet-200'
      }`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-violet-600 animate-pulse" />
          <span className="text-xs font-bold text-violet-600 uppercase tracking-wider">Today's Daily Quest</span>
          <span className="text-xs text-gray-400">· resets midnight</span>
        </div>
        {isCompleted ? (
          <span className="text-xs px-3 py-1 rounded-full border font-bold bg-emerald-50 text-emerald-700 border-emerald-200 shadow-sm">
            ✓ Completed!
          </span>
        ) : (
          <span className={`text-xs px-3 py-1 rounded-full border ${diff.classes}`}>
            {diff.label}
          </span>
        )}
      </div>

      <div className="flex items-start gap-4 mb-4">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-100 to-indigo-100 text-violet-700 flex items-center justify-center text-3xl shadow-sm shrink-0">
          {SPORT_EMOJI[data.sport] || '🎯'}
        </div>
        <div>
          <h2 className="text-xl font-extrabold text-gray-900 leading-tight">
            {data.title}
          </h2>
          <p className="text-gray-500 text-sm mt-1">{data.description}</p>
        </div>
      </div>

      {/* Target pills */}
      <div className="grid grid-cols-3 gap-2.5 mb-5">
        <div className="bg-gray-50 rounded-2xl p-3 text-center border border-gray-100">
          <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Sport</div>
          <div className="text-sm font-bold text-gray-800 capitalize mt-0.5">{data.sport}</div>
        </div>
        <div className="bg-gray-50 rounded-2xl p-3 text-center border border-gray-100">
          <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Target</div>
          <div className="text-sm font-bold text-gray-800 mt-0.5">{targetDisplay}</div>
        </div>
        <div className="bg-violet-50 rounded-2xl p-3 text-center border border-violet-100">
          <div className="text-[11px] font-bold text-violet-600 uppercase tracking-wider">Difficulty</div>
          <div className="text-sm font-bold text-violet-700 capitalize mt-0.5">{diff.label}</div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="flex justify-between items-center text-xs font-semibold mb-2">
          <span className="text-gray-500">Your Progress</span>
          <span className={isCompleted ? 'text-emerald-600 font-bold' : 'text-gray-900 font-bold'}>
            {myProgress.toFixed(1)} / {target} {metricLabel} ({progressPct}%)
          </span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
          <div
            className={`h-3 rounded-full transition-all duration-700 ${isCompleted
                ? 'bg-gradient-to-r from-emerald-500 to-green-500'
                : 'bg-gradient-to-r from-violet-600 to-indigo-500'
              }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
        {isCompleted && (
          <p className="text-xs text-emerald-600 mt-2 font-bold flex items-center gap-1">
            <span>🎉</span> Quest complete! Goal achieved.
          </p>
        )}
      </div>

      {data.coach_note && (
        <div className="bg-violet-50/60 border border-violet-100 rounded-2xl p-3.5 flex gap-2.5 items-start">
          <span className="text-base">💡</span>
          <p className="text-xs text-gray-600 leading-relaxed font-medium">{data.coach_note}</p>
        </div>
      )}

      {!isCompleted && (
        <button
          onClick={() => {
            const isPoints = data.metric?.type === 'points'
            navigate(
              `/log?sport=${data.sport || 'running'}&title=${encodeURIComponent(data.title)}${isPoints ? `&points_target=${target}` : `&target=${target}`
              }`
            )
          }}
          className="w-full mt-2 py-3 rounded-2xl bg-violet-600 hover:bg-violet-700 active:scale-[0.99] text-white text-xs font-bold transition-all flex items-center justify-center gap-1.5 shadow-md shadow-violet-200"
        >
          <span>⚡</span> Log Workout for Today's Quest →
        </button>
      )}
    </div>
  )
}

function CreateChallengeForm({
  userId,
  initialFriendId,
  onCreated,
}: {
  userId: string
  initialFriendId?: string | null
  onCreated: () => void
}) {
  const [form, setForm] = useState({
    title: '',
    description: '',
    sport: '',
    metric_type: 'distance_km',
    target_value: '',
    difficulty: 'medium',
  })
  const [selectedFriendIds, setSelectedFriendIds] = useState<string[]>(
    initialFriendId ? [initialFriendId] : []
  )
  const [customUsername, setCustomUsername] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  const { data: friendsData } = useQuery({
    queryKey: ['friends', userId],
    queryFn: () => getFriends(),
    staleTime: 30_000,
  })

  useEffect(() => {
    if (initialFriendId && !selectedFriendIds.includes(initialFriendId)) {
      setSelectedFriendIds(prev => [...prev, initialFriendId])
    }
  }, [initialFriendId])

  const toggleFriend = (id: string) => {
    setSelectedFriendIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const addCustomFriend = () => {
    const trimmed = customUsername.trim().replace(/^@/, '')
    if (trimmed && !selectedFriendIds.includes(trimmed)) {
      setSelectedFriendIds(prev => [...prev, trimmed])
      setCustomUsername('')
    }
  }

  const mutation = useMutation({
    mutationFn: () => {
      const invitees = [...selectedFriendIds]
      if (customUsername.trim()) {
        const trimmed = customUsername.trim().replace(/^@/, '')
        if (!invitees.includes(trimmed)) {
          invitees.push(trimmed)
        }
      }

      return createChallenge({
        title: form.title,
        description: form.description || undefined,
        sport: form.sport || undefined,
        metric_type: form.metric_type,
        target_value: parseFloat(form.target_value),
        bonus_points: 0,
        difficulty: form.difficulty,
        invitee_ids: invitees,
      })
    },
    onSuccess: () => {
      onCreated()
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.message || 'Failed to create challenge'
      setErrorMsg(typeof msg === 'string' ? msg : JSON.stringify(msg))
    },
  })

  return (
    <div className="bg-white border border-gray-100 rounded-3xl p-6 sm:p-7 space-y-5 shadow-sm">
      <div className="flex items-center justify-between pb-3 border-b border-gray-100">
        <h3 className="font-extrabold text-gray-900 text-lg flex items-center gap-2">
          <span>🎯</span> Create Challenge with Friends
        </h3>
        {selectedFriendIds.length > 0 && (
          <span className="text-xs bg-violet-50 text-violet-700 border border-violet-200 px-3 py-1 rounded-full font-bold">
            {selectedFriendIds.length} friend{selectedFriendIds.length > 1 ? 's' : ''} invited
          </span>
        )}
      </div>

      {errorMsg && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-2xl px-4 py-3 text-sm">
          {errorMsg}
        </div>
      )}

      {/* Friend Selection */}
      <div className="bg-gray-50/70 border border-gray-100 rounded-2xl p-4 space-y-3">
        <label className="block text-xs font-bold text-violet-700 uppercase tracking-wider">
          Invite Friends
        </label>

        {friendsData?.friends && friendsData.friends.length > 0 ? (
          <div className="space-y-2">
            <p className="text-xs text-gray-500">Select friends to compete against:</p>
            <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto pr-1">
              {friendsData.friends.map((f: any) => {
                const isSelected = selectedFriendIds.includes(f.user_id)
                return (
                  <button
                    key={f.user_id}
                    type="button"
                    onClick={() => toggleFriend(f.user_id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${isSelected
                        ? 'bg-violet-600 border-violet-600 text-white shadow-sm shadow-violet-200'
                        : 'bg-white border-gray-200 text-gray-700 hover:border-violet-300'
                      }`}
                  >
                    <span>{isSelected ? '✓' : '👤'}</span>
                    <span>{f.first_name}</span>
                    {f.username && <span className="opacity-75">(@{f.username})</span>}
                  </button>
                )
              })}
            </div>
          </div>
        ) : (
          <p className="text-xs text-gray-400">
            No accepted friends yet. Add friends on the Friends tab, or invite by handle below!
          </p>
        )}

        <div className="pt-2 border-t border-gray-200">
          <label className="block text-xs text-gray-500 mb-1.5">
            Or invite by athlete handle:
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={customUsername}
              onChange={e => setCustomUsername(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  addCustomFriend()
                }
              }}
              placeholder="e.g. alice_chen"
              className="flex-1 bg-white border border-gray-200 text-gray-900 rounded-xl px-3.5 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-violet-400"
            />
            <button
              type="button"
              onClick={addCustomFriend}
              disabled={!customUsername.trim()}
              className="btn-ghost !py-2 !px-4 !text-xs !rounded-xl"
            >
              Add
            </button>
          </div>
          {selectedFriendIds.filter(id => !friendsData?.friends?.some((f: any) => f.user_id === id)).length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {selectedFriendIds
                .filter(id => !friendsData?.friends?.some((f: any) => f.user_id === id))
                .map(uname => (
                  <span
                    key={uname}
                    className="inline-flex items-center gap-1 bg-violet-50 border border-violet-200 text-violet-700 text-xs px-2.5 py-0.5 rounded-full font-mono font-bold"
                  >
                    @{uname}
                    <button
                      type="button"
                      onClick={() => toggleFriend(uname)}
                      className="hover:text-red-500 ml-1 text-sm leading-none"
                    >
                      ×
                    </button>
                  </span>
                ))}
            </div>
          )}
        </div>
      </div>

      <div>
        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Challenge Title *</label>
        <input
          className="fit-input !py-3"
          placeholder="e.g. Weekend 10K Showdown"
          value={form.title}
          onChange={e => setForm({ ...form, title: e.target.value })}
          maxLength={100}
        />
      </div>

      <div>
        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Description (Optional)</label>
        <input
          className="fit-input !py-3"
          placeholder="e.g. First one to cross the line earns ultimate bragging rights!"
          value={form.description}
          onChange={e => setForm({ ...form, description: e.target.value })}
          maxLength={200}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Sport (Optional)</label>
          <select
            className="fit-input !py-3 bg-white"
            value={form.sport}
            onChange={e => {
              const sp = e.target.value
              let nextMetric = 'points'
              if (sp === 'running' || sp === 'walking' || sp === 'cycling') nextMetric = 'distance_km'
              else if (sp === 'gym' || sp === 'swimming') nextMetric = 'duration_minsec'
              else if (sp === 'steps') nextMetric = 'count'
              setForm({ ...form, sport: sp, metric_type: nextMetric })
            }}
          >
            <option value="">Any sport</option>
            {['running', 'walking', 'cycling', 'gym', 'swimming', 'steps'].map(s => (
              <option key={s} value={s}>{SPORT_EMOJI[s]} {s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Metric Type</label>
          <select
            className="fit-input !py-3 bg-white"
            value={form.metric_type}
            onChange={e => setForm({ ...form, metric_type: e.target.value })}
          >
            {(!form.sport || form.sport === 'running' || form.sport === 'walking' || form.sport === 'cycling') && (
              <option value="distance_km">Distance (km)</option>
            )}
            {(!form.sport || form.sport === 'gym' || form.sport === 'swimming') && (
              <option value="duration_minsec">Duration (min)</option>
            )}
            {(!form.sport || form.sport === 'steps') && (
              <option value="count">Count / Steps</option>
            )}
            <option value="points">Points</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">
          Target Value ({form.metric_type === 'points' ? 'Points' : form.metric_type === 'distance_km' ? 'km' : form.metric_type === 'duration_minsec' ? 'minutes' : 'steps'}) *
        </label>
        <input
          type="number"
          min={1}
          step={form.metric_type === 'count' || form.metric_type === 'points' ? 1 : 0.1}
          className="fit-input !py-3"
          placeholder={form.metric_type === 'points' ? "e.g. 500 points" : form.metric_type === 'count' ? "e.g. 10000 steps" : "e.g. 10"}
          value={form.target_value}
          onChange={e => setForm({ ...form, target_value: e.target.value })}
        />
      </div>

      <div>
        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Difficulty</label>
        <div className="flex gap-2">
          {(['easy', 'medium', 'hard'] as const).map(d => (
            <button
              key={d}
              type="button"
              onClick={() => setForm({ ...form, difficulty: d })}
              className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-all capitalize ${form.difficulty === d
                  ? DIFFICULTY_CONFIG[d].classes + ' ring-2 ring-violet-400'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={() => { setErrorMsg(''); mutation.mutate() }}
        disabled={mutation.isPending || !form.title.trim() || !form.target_value}
        className="w-full btn-primary !rounded-2xl !py-3.5"
      >
        {mutation.isPending
          ? 'Creating Challenge…'
          : selectedFriendIds.length > 0
            ? `Create & Invite ${selectedFriendIds.length} Friend${selectedFriendIds.length > 1 ? 's' : ''}`
            : 'Create Challenge'}
      </button>
    </div>
  )
}

export default function ChallengesPage() {
  const userId = useUserStore(s => s.userId)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const qc = useQueryClient()

  const friendIdParam = searchParams.get('friendId')
  const [showCreate, setShowCreate] = useState(!!friendIdParam)
  const [feedback, setFeedback] = useState<{ type: 'ok' | 'err'; msg: string } | null>(null)

  const { data: challengesData } = useQuery({
    queryKey: ['user-challenges', userId],
    queryFn: () => getChallenges(),
    enabled: !!userId,
    staleTime: 5_000,
  })

  const respondMutation = useMutation({
    mutationFn: ({ challengeId, action }: { challengeId: string; action: 'accept' | 'decline' }) =>
      respondChallenge(challengeId, action),
    onSuccess: (_, vars) => {
      setFeedback({
        type: 'ok',
        msg: vars.action === 'accept' ? 'Challenge accepted! Go crush it!' : 'Challenge invitation declined.',
      })
      qc.invalidateQueries({ queryKey: ['user-challenges', userId] })
    },
    onError: (err: any) => {
      setFeedback({ type: 'err', msg: err.message || 'Action failed' })
    },
  })

  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const deleteMutation = useMutation({
    mutationFn: (challengeId: string) => deleteChallenge(challengeId),
    onSuccess: () => {
      setFeedback({ type: 'ok', msg: 'Challenge deleted successfully.' })
      setConfirmDeleteId(null)
      qc.invalidateQueries({ queryKey: ['user-challenges', userId] })
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.message || 'Failed to delete challenge'
      setFeedback({ type: 'err', msg: typeof msg === 'string' ? msg : JSON.stringify(msg) })
      setConfirmDeleteId(null)
    },
  })

  if (!userId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-4 text-center">
        <div className="w-20 h-20 rounded-3xl bg-violet-100 flex items-center justify-center text-4xl shadow-sm text-violet-600">
          🏆
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900">Challenges & Quests</h2>
          <p className="text-sm text-gray-500 max-w-sm mt-1">
            Register or sign in to tackle AI daily challenges and create head-to-head competitions with friends.
          </p>
        </div>
        <button
          onClick={() => navigate('/register')}
          className="btn-primary"
        >
          Sign In / Register
        </button>
      </div>
    )
  }

  const allChallenges: UserChallenge[] = challengesData?.challenges || []
  const incomingInvites = allChallenges.filter(c => c.my_status === 'invited')
  const activeChallenges = allChallenges.filter(c => (c.my_status === 'accepted' || c.is_creator) && !c.is_daily)

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold text-violet-600 uppercase tracking-widest mb-0.5">Competitions</p>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Challenges</h1>
          <p className="text-sm text-gray-500 mt-0.5">Push your limits with daily quests & head-to-head matches</p>
        </div>
        <button
          onClick={() => setShowCreate(v => !v)}
          className="btn-primary !rounded-2xl !py-2.5 !px-4 !text-sm flex items-center gap-1.5 shadow-md shadow-violet-200"
        >
          <span>{showCreate ? '✕' : '+'}</span>
          <span>{showCreate ? 'Close Form' : 'New Challenge'}</span>
        </button>
      </div>

      {feedback && (
        <div
          className={`text-sm rounded-2xl p-4 flex items-center gap-3 shadow-sm border ${feedback.type === 'ok'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}
        >
          <span className="text-xl">{feedback.type === 'ok' ? '🎉' : '⚠️'}</span>
          <span className="font-medium flex-1">{feedback.msg}</span>
          <button
            onClick={() => setFeedback(null)}
            className="text-gray-400 hover:text-gray-600 font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Challenge Creation Form */}
      {showCreate && (
        <CreateChallengeForm
          userId={userId}
          initialFriendId={friendIdParam}
          onCreated={() => {
            setShowCreate(false)
            setFeedback({ type: 'ok', msg: 'Challenge created successfully! Friends have been invited.' })
            qc.invalidateQueries({ queryKey: ['user-challenges', userId] })
          }}
        />
      )}

      {/* Incoming Friend Challenge Invites */}
      {incomingInvites.length > 0 && (
        <div className="bg-white border-2 border-violet-200 rounded-3xl p-6 space-y-3 shadow-md shadow-violet-100">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-gray-900 flex items-center gap-2 text-base">
              <span>📬</span> Friend Challenge Invites
              <span className="bg-violet-600 text-white text-xs px-2.5 py-0.5 rounded-full font-bold">
                {incomingInvites.length} new
              </span>
            </h3>
          </div>
          <p className="text-xs text-gray-500">
            Your friends challenged you! Accept to compete side-by-side.
          </p>

          <div className="space-y-3 mt-2">
            {incomingInvites.map(ch => (
              <div
                key={ch.id}
                className="bg-gray-50/80 border border-gray-100 rounded-2xl p-4 space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-xs text-violet-600 font-bold mb-0.5">
                      Challenged by {ch.creator_name} {ch.creator_username ? `(@${ch.creator_username})` : ''}
                    </div>
                    <div className="text-base font-extrabold text-gray-900 flex items-center gap-2">
                      <span>{ch.sport ? SPORT_EMOJI[ch.sport] || '🎯' : '🎯'}</span>
                      <span>{ch.title}</span>
                    </div>
                    {ch.description && (
                      <p className="text-xs text-gray-500 mt-1">{ch.description}</p>
                    )}
                  </div>
                  <span className="text-xs px-2.5 py-1 rounded-full border font-semibold bg-amber-50 text-amber-700 border-amber-200 capitalize shrink-0">
                    {ch.difficulty}
                  </span>
                </div>

                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="bg-white text-gray-700 px-3 py-1 rounded-full border border-gray-200 font-medium">
                    🎯 Target: {ch.target_value} {getMetricUnit(ch.metric_type)}
                  </span>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={() => respondMutation.mutate({ challengeId: ch.id, action: 'accept' })}
                    disabled={respondMutation.isPending}
                    className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm"
                  >
                    Accept Challenge
                  </button>
                  <button
                    onClick={() => respondMutation.mutate({ challengeId: ch.id, action: 'decline' })}
                    disabled={respondMutation.isPending}
                    className="bg-gray-100 hover:bg-gray-200 disabled:opacity-50 text-gray-600 px-4 py-2 rounded-xl text-xs font-semibold transition-colors"
                  >
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Friend Challenges */}
      {activeChallenges.length > 0 && (
        <div className="bg-white border border-gray-100 rounded-3xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-extrabold text-gray-900 text-lg flex items-center gap-2">
              <span>🤝</span> Active Friend Challenges ({activeChallenges.length})
            </h3>
          </div>

          <div className="space-y-3">
            {activeChallenges.map(ch => {
              const progressPct = Math.min(100, Math.round((ch.my_progress / (ch.target_value || 1)) * 100))
              const isComplete = ch.my_progress >= ch.target_value

              return (
                <div
                  key={ch.id}
                  onClick={() => {
                    const isPoints = ch.metric_type === 'points'
                    const query = new URLSearchParams({
                      sport: ch.sport || 'running',
                      title: ch.title,
                      target: String(ch.target_value),
                      metric_type: ch.metric_type,
                    })
                    if (isPoints) {
                      query.set('points_target', String(ch.target_value))
                    }
                    navigate(`/log?${query.toString()}`)
                  }}
                  className="bg-gray-50/70 hover:bg-violet-50/40 border border-gray-100 hover:border-violet-200 rounded-2xl p-4 sm:p-5 space-y-3 cursor-pointer transition-all shadow-xs"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{ch.sport ? SPORT_EMOJI[ch.sport] || '🎯' : '🎯'}</span>
                        <h4 className="font-bold text-gray-900 text-base">{ch.title}</h4>
                      </div>
                      <div className="text-xs text-gray-400 mt-1 flex items-center gap-2">
                        <span>
                          {ch.is_creator ? 'Created by you' : `Created by ${ch.creator_name}`}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {isComplete ? (
                        <span className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1 rounded-full font-bold">
                          ✓ Completed
                        </span>
                      ) : (
                        <span className="text-xs bg-violet-50 text-violet-700 border border-violet-200 px-3 py-1 rounded-full font-bold">
                          {progressPct}% Done
                        </span>
                      )}

                      {ch.is_creator && (
                        <div onClick={(e) => e.stopPropagation()} className="shrink-0">
                          {confirmDeleteId === ch.id ? (
                            <div className="flex items-center gap-1.5 bg-rose-50 border border-rose-200 rounded-xl px-2 py-1">
                              <span className="text-[11px] font-bold text-rose-700">Delete?</span>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  deleteMutation.mutate(ch.id)
                                }}
                                disabled={deleteMutation.isPending}
                                className="px-2 py-0.5 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-colors"
                              >
                                Yes
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setConfirmDeleteId(null)
                                }}
                                className="px-1.5 py-0.5 bg-white text-gray-600 hover:text-gray-900 rounded-lg text-xs font-semibold border border-gray-200"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                setConfirmDeleteId(ch.id)
                              }}
                              title="Delete challenge"
                              className="p-1.5 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {ch.description && (
                    <p className="text-xs text-gray-600">{ch.description}</p>
                  )}

                  {/* Progress bar */}
                  <div>
                    <div className="flex justify-between text-xs text-gray-500 mb-1.5 font-semibold">
                      <span>Your Progress</span>
                      <span className="text-gray-900 font-bold">
                        {ch.my_progress.toFixed(ch.metric_type === 'points' || ch.metric_type === 'count' ? 0 : 1)} / {ch.target_value} {getMetricUnit(ch.metric_type)}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-violet-600 to-indigo-500 h-2.5 rounded-full transition-all"
                        style={{ width: `${progressPct}%` }}
                      />
                    </div>
                  </div>

                  {/* Participants summary */}
                  {ch.participants && ch.participants.length > 0 && (
                    <div className="pt-2 border-t border-gray-200/80">
                      <span className="text-[11px] text-gray-400 font-bold uppercase tracking-wider block mb-1.5">
                        Competitors ({ch.participants.length}):
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {ch.participants.map(p => (
                          <div
                            key={p.user_id}
                            className={`flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold border ${p.user_id === userId
                                ? 'bg-violet-50 border-violet-200 text-violet-700'
                                : 'bg-white border-gray-200 text-gray-700'
                              }`}
                          >
                            <span>{p.status === 'completed' ? '🏆' : p.status === 'accepted' ? '🏃' : '⏳'}</span>
                            <span>{p.first_name}</span>
                            <span className="text-[11px] text-gray-400">({p.progress.toFixed(1)})</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Card bottom CTA */}
                  <div className="pt-2 flex items-center justify-between border-t border-gray-200/60">
                    <span className="text-[11px] text-gray-400">Click to record workout progress</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        const isPoints = ch.metric_type === 'points'
                        const query = new URLSearchParams({
                          sport: ch.sport || 'running',
                          title: ch.title,
                          metric_type: ch.metric_type,
                        })
                        if (isPoints) {
                          query.set('points_target', String(ch.target_value))
                        } else {
                          query.set('target', String(ch.target_value))
                        }
                        navigate(`/log?${query.toString()}`)
                      }}
                      className="text-xs font-bold text-violet-600 hover:text-violet-700 hover:underline flex items-center gap-1"
                    >
                      Log Workout →
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Today's AI Challenge */}
      <DailyCard userId={userId} />

      {/* Bottom invitation card */}
      <div className="bg-gradient-to-r from-violet-50 to-indigo-50 border border-violet-100 rounded-3xl p-6 text-center space-y-3">
        <div className="w-12 h-12 rounded-2xl bg-violet-600 text-white flex items-center justify-center text-2xl mx-auto shadow-md shadow-violet-200">
          🤝
        </div>
        <h4 className="text-base font-extrabold text-gray-900">Challenge Your Friends</h4>
        <p className="text-gray-500 text-xs max-w-md mx-auto leading-relaxed">
          Create customized fitness goals, set distances or reps and bonus rewards, and invite friends to see who finishes first!
        </p>
        {!showCreate && (
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary !py-2.5 !px-5 !text-xs !rounded-2xl inline-block"
          >
            Create a Friend Challenge
          </button>
        )}
      </div>
    </div>
  )
}
