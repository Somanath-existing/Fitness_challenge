import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { logActivity } from '../api/endpoints'
import { useUserStore } from '../stores/userStore'
import type { SportType } from '../types'

interface SportOption {
  type: SportType
  label: string
  emoji: string
  metric: string
  placeholder: string
  bgColor: string
  textColor: string
  borderColor: string
  bgLight: string
  accentColor: string
}

const SPORTS: SportOption[] = [
  {
    type: 'running',
    label: 'Running',
    emoji: '🏃‍♂️',
    metric: 'distance_km',
    placeholder: '5.2',
    bgColor: 'bg-violet-600',
    textColor: 'text-violet-700',
    borderColor: 'border-violet-200',
    bgLight: 'bg-violet-50',
    accentColor: '#6366f1',
  },
  {
    type: 'walking',
    label: 'Walking',
    emoji: '🚶‍♀️',
    metric: 'distance_km',
    placeholder: '3.5',
    bgColor: 'bg-emerald-600',
    textColor: 'text-emerald-700',
    borderColor: 'border-emerald-200',
    bgLight: 'bg-emerald-50',
    accentColor: '#10b981',
  },
  {
    type: 'cycling',
    label: 'Cycling',
    emoji: '🚴‍♂️',
    metric: 'distance_km',
    placeholder: '18.4',
    bgColor: 'bg-amber-500',
    textColor: 'text-amber-700',
    borderColor: 'border-amber-200',
    bgLight: 'bg-amber-50',
    accentColor: '#f59e0b',
  },
  {
    type: 'gym',
    label: 'Strength / Gym',
    emoji: '🏋️‍♂️',
    metric: 'duration_minsec',
    placeholder: '45:00',
    bgColor: 'bg-rose-500',
    textColor: 'text-rose-700',
    borderColor: 'border-rose-200',
    bgLight: 'bg-rose-50',
    accentColor: '#f43f5e',
  },
  {
    type: 'swimming',
    label: 'Swimming',
    emoji: '🏊‍♂️',
    metric: 'duration_minsec',
    placeholder: '30:00',
    bgColor: 'bg-sky-500',
    textColor: 'text-sky-700',
    borderColor: 'border-sky-200',
    bgLight: 'bg-sky-50',
    accentColor: '#0ea5e9',
  },
  {
    type: 'steps',
    label: 'Daily Steps',
    emoji: '👣',
    metric: 'count',
    placeholder: '8400',
    bgColor: 'bg-indigo-600',
    textColor: 'text-indigo-700',
    borderColor: 'border-indigo-200',
    bgLight: 'bg-indigo-50',
    accentColor: '#4f46e5',
  },
]

const SCORING_HINT: Record<SportType, string> = {
  running: '100 points per km',
  walking: '50 points per km',
  cycling: '25 points per km',
  gym: '5 points per minute',
  swimming: '15 points per minute',
  steps: '1 point per 100 steps',
}

export default function LogActivityPage() {
  const userId = useUserStore((s) => s.userId)
  const firstName = useUserStore((s) => s.firstName)
  const updatePoints = useUserStore((s) => s.updatePoints)
  const qc = useQueryClient()

  const [searchParams] = useSearchParams()
  const paramSport = searchParams.get('sport') as SportType | null
  const paramTitle = searchParams.get('title')
  const paramTarget = searchParams.get('target')

  const initialSport: SportType =
    paramSport && SPORTS.some((s) => s.type === paramSport) ? paramSport : 'running'

  const [sport, setSport] = useState<SportType>(initialSport)
  const [value, setValue] = useState(paramTarget ? String(paramTarget) : '')
  const [title, setTitle] = useState(paramTitle ? `Quest: ${paramTitle}` : '')
  const [notes, setNotes] = useState('')
  const [success, setSuccess] = useState<{ points: number; badges: string[] } | null>(null)
  const [error, setError] = useState('')

  const current = SPORTS.find((s) => s.type === sport)!

  const mutation = useMutation({
    mutationFn: () =>
      logActivity({
        sport,
        metric: { type: current.metric, value: value.trim() },
        title: title.trim() || undefined,
        notes: notes.trim() || undefined,
      }),
    onSuccess: (data) => {
      setSuccess({ points: data.points_awarded, badges: data.new_badges })
      updatePoints(data.user_total_points)
      qc.invalidateQueries({ queryKey: ['leaderboard'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      qc.invalidateQueries({ queryKey: ['daily-challenge'] })
      qc.invalidateQueries({ queryKey: ['user-challenges'] })
      setValue('')
      setTitle('')
      setNotes('')
    },
    onError: (err: Error) => {
      setError(err.message)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!userId) {
      setError('Please sign in or register to log your workouts.')
      return
    }
    if (!value.trim()) {
      setError('Please enter the metric for this workout.')
      return
    }
    setError('')
    setSuccess(null)
    mutation.mutate()
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Top Header greeting in style of reference */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-sm font-semibold text-violet-600 mb-0.5">Let's check your activity</p>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">
            Log Workout
          </h1>
        </div>
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white text-xl shadow-md shadow-violet-200">
          {firstName ? firstName[0].toUpperCase() : '⚡'}
        </div>
      </div>

      {/* Sport Category Grid */}
      <div className="mb-6">
        <label className="text-xs font-bold text-gray-500 uppercase tracking-wider block mb-3">
          Select Workout Type
        </label>
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2.5">
          {SPORTS.map((s) => {
            const isSelected = sport === s.type
            return (
              <button
                key={s.type}
                type="button"
                id={`sport-btn-${s.type}`}
                onClick={() => {
                  setSport(s.type)
                  setValue('')
                  setError('')
                }}
                className={`flex flex-col items-center justify-center p-3 rounded-2xl border transition-all duration-200 ${
                  isSelected
                    ? 'bg-violet-600 text-white border-violet-600 shadow-md shadow-violet-200 scale-102'
                    : 'bg-white text-gray-700 border-gray-100 hover:border-violet-200 hover:bg-violet-50/50 shadow-sm'
                }`}
              >
                <span className="text-2xl mb-1">{s.emoji}</span>
                <span className={`text-xs font-semibold text-center leading-tight ${isSelected ? 'text-white' : 'text-gray-800'}`}>
                  {s.label}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Challenge Notice */}
      {paramTitle && (
        <div className="bg-gradient-to-r from-violet-50 to-indigo-50 border border-violet-200 rounded-2xl p-4 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🎯</span>
            <div>
              <span className="text-[11px] font-bold text-violet-600 uppercase tracking-wider block">Logging for Challenge</span>
              <span className="text-sm font-extrabold text-gray-900">{paramTitle}</span>
            </div>
          </div>
          {paramTarget && (
            <span className="text-xs bg-white text-violet-700 px-3 py-1 rounded-xl font-bold border border-violet-100 shadow-xs">
              Target: {paramTarget}
            </span>
          )}
        </div>
      )}

      {/* Main Logging Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-100 relative overflow-hidden">
        {/* Soft decorative background pill */}
        <div className="flex items-center justify-between pb-5 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-2xl ${current.bgLight} ${current.textColor} flex items-center justify-center text-2xl`}>
              {current.emoji}
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">{current.label}</h2>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700">
                ⚡ {SCORING_HINT[sport]}
              </span>
            </div>
          </div>
          <span className="text-xs font-bold text-gray-400 bg-gray-50 px-3 py-1.5 rounded-xl border border-gray-100">
            {current.metric === 'distance_km' ? 'Distance' : current.metric === 'count' ? 'Steps' : 'Duration'}
          </span>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Main Numeric Metric Input */}
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
              {current.metric === 'distance_km' && 'Total Distance (km)'}
              {current.metric === 'duration_minsec' && 'Total Duration (MM:SS or Minutes)'}
              {current.metric === 'count' && 'Total Step Count'}
            </label>
            <div className="relative">
              <input
                id="activity-metric-input"
                className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-2xl px-5 py-4 text-2xl font-bold font-mono focus:bg-white focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all placeholder:text-gray-300"
                placeholder={current.placeholder}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                inputMode={current.metric === 'count' ? 'numeric' : 'decimal'}
              />
              <span className="absolute right-5 top-1/2 -translate-y-1/2 text-sm font-bold text-gray-400">
                {current.metric === 'distance_km' && 'km'}
                {current.metric === 'duration_minsec' && 'min'}
                {current.metric === 'count' && 'steps'}
              </span>
            </div>
          </div>

          {/* Activity Title */}
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
              Session Title (Optional)
            </label>
            <input
              id="activity-title-input"
              className="fit-input !py-3.5"
              placeholder="e.g. Morning Sunrise Run, Power Yoga Flow"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={100}
            />
          </div>

          {/* Activity Notes */}
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
              Session Notes (Optional)
            </label>
            <textarea
              id="activity-notes-input"
              className="fit-input !py-3 resize-none"
              placeholder="How did it feel? Pace, heart rate, or highlights..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={500}
              rows={2}
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-2xl px-4 py-3 text-sm flex items-center gap-2">
              <span>⚠️</span>
              <span className="font-medium">{error}</span>
            </div>
          )}

          {/* Success Banner */}
          {success && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl p-4 flex items-start gap-3">
              <span className="text-2xl">🎉</span>
              <div>
                <div className="font-bold text-base text-emerald-900">
                  +{success.points} points awarded!
                </div>
                <p className="text-xs text-emerald-700 mt-0.5">
                  Great job staying active! Your streak and challenge progress have been updated.
                </p>
                {success.badges.length > 0 && (
                  <div className="mt-2 inline-flex items-center gap-1.5 bg-white text-emerald-800 text-xs font-bold px-3 py-1 rounded-full shadow-sm border border-emerald-200">
                    <span>🏅</span>
                    New Badge: {success.badges.join(', ')}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Submit Button in style of the reference UI */}
          <button
            id="log-activity-submit"
            type="submit"
            disabled={mutation.isPending || !userId}
            className="w-full bg-violet-600 hover:bg-violet-700 active:bg-violet-800 disabled:opacity-50 text-white font-bold rounded-2xl py-4 text-base transition-all duration-200 shadow-lg shadow-violet-200 flex items-center justify-center gap-2 cursor-pointer"
          >
            {mutation.isPending ? (
              <>
                <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Logging Workout...</span>
              </>
            ) : (
              <span>Save & Log Workout</span>
            )}
          </button>

          {!userId && (
            <p className="text-center text-xs text-gray-400">
              Please sign in or create an account to record your workouts.
            </p>
          )}
        </form>
      </div>

      {/* Motivational widget matching reference card */}
      <div className="mt-6 bg-gradient-to-r from-violet-50 to-purple-50 rounded-2xl p-4 border border-violet-100 flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-violet-600 text-white flex items-center justify-center text-lg font-bold shrink-0">
          ✨
        </div>
        <div>
          <h4 className="text-sm font-bold text-gray-900">Keep the progress!</h4>
          <p className="text-xs text-gray-600">
            Logging daily activities builds your streak and unlocks high-tier achievements.
          </p>
        </div>
      </div>
    </div>
  )
}
