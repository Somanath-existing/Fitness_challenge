import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import ActivityCalendar from 'react-activity-calendar'
import { getDashboard, getInsights, getActivities, recomputeStreaks } from '../api/endpoints'
import { useUserStore } from '../stores/userStore'
import TierBadge from '../components/TierBadge'
import StreakBadge from '../components/StreakBadge'
import { formatActivityDate } from '../utils/date'
import type { Tier } from '../types'

const SPORT_COLORS: Record<string, string> = {
  running:  '#7c3aed',
  walking:  '#06b6d4',
  cycling:  '#f59e0b',
  gym:      '#ef4444',
  swimming: '#3b82f6',
  steps:    '#10b981',
}

const SPORT_EMOJI: Record<string, string> = {
  running: '🏃‍♂️', walking: '🚶‍♀️', cycling: '🚴‍♂️',
  gym: '🏋️‍♂️', swimming: '🏊‍♂️', steps: '👣',
}

const BADGE_LABELS: Record<string, string> = {
  first_step:        '🌟 First Step',
  '7day_warrior':    '🔥 7-Day Warrior',
  '30day_legend':    '🏅 30-Day Legend',
  marathon_runner:   '🏃 Marathon Runner',
  iron_human:        '🦾 Iron Human',
  point_machine:     '⚡ Point Machine',
  challenge_victor:  '🏆 Challenge Victor',
}


function InsightsPanel({ userId }: { userId: string }) {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['insights', userId],
    queryFn: () => getInsights(userId),
    staleTime: 60 * 60 * 1000,
    retry: false,
  })

  return (
    <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs font-bold text-violet-600 uppercase tracking-widest mb-0.5">AI Coach</p>
          <h3 className="font-extrabold text-gray-900 text-base">Coaching Insights</h3>
        </div>
        <button
          id="refresh-insights"
          onClick={() => refetch()}
          disabled={isFetching}
          className="btn-ghost !py-1.5 !px-3 !text-xs !rounded-xl"
        >
          {isFetching ? 'Refreshing…' : '↻ Refresh'}
        </button>
      </div>
      {isLoading && (
        <div className="space-y-3">
          {[0, 1, 2].map(i => (
            <div key={i} className="h-16 bg-gray-50 rounded-2xl animate-pulse" />
          ))}
        </div>
      )}
      {data?.insights && (
        <div className="space-y-3">
          {data.insights.map((insight, i) => (
            <div key={i} className="flex gap-3 bg-violet-50/50 rounded-2xl p-3.5 border border-violet-100">
              <span className="text-2xl shrink-0">{insight.icon}</span>
              <div>
                <div className="text-sm font-bold text-gray-900">{insight.title}</div>
                <div className="text-xs text-gray-600 mt-0.5 leading-relaxed">{insight.text}</div>
              </div>
            </div>
          ))}
        </div>
      )}
      {!isLoading && (isError || !data) && (
        <div className="text-sm text-gray-400 text-center py-4">
          {isError
            ? 'Too many requests — please wait a moment and refresh.'
            : 'Insights unavailable right now — check back soon.'}
        </div>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const userId = useUserStore((s) => s.userId)
  const firstName = useUserStore((s) => s.firstName)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeSport, setActiveSport] = useState<string | null>(null)
  const [showAllActivities, setShowAllActivities] = useState(false)
  const [activityPage, setActivityPage] = useState(0)
  const PAGE_SIZE = 20

  // Auto-recompute streaks once per session to fix seeded users
  const recomputeMutation = useMutation({
    mutationFn: recomputeStreaks,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dashboard', userId] }),
  })
  useEffect(() => {
    if (userId) recomputeMutation.mutate()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId])

  // Paginated full activity list (only fetched when panel is open)
  const { data: allActivitiesData, isFetching: loadingMore } = useQuery({
    queryKey: ['all-activities', userId, activityPage],
    queryFn: () => getActivities({ limit: PAGE_SIZE, offset: activityPage * PAGE_SIZE }),
    enabled: !!userId && showAllActivities,
    staleTime: 30_000,
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', userId],
    queryFn: () => getDashboard(userId!),
    enabled: !!userId,
    staleTime: 30_000,
  })

  if (!userId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-4 text-center">
        <div className="w-20 h-20 rounded-3xl bg-violet-100 flex items-center justify-center text-4xl shadow-sm text-violet-600">
          🏃
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900">Your Activity Hub</h2>
          <p className="text-sm text-gray-500 max-w-sm mt-1">
            Sign in or create an account to view your personalized dashboard, workouts, and analytics.
          </p>
        </div>
        <button
          id="dashboard-get-started"
          onClick={() => navigate('/register')}
          className="btn-primary"
        >
          Sign In / Register
        </button>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-5">
        <div className="h-28 bg-white rounded-3xl animate-pulse shadow-sm" />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[0, 1, 2].map(i => <div key={i} className="h-28 bg-white rounded-3xl animate-pulse shadow-sm" />)}
        </div>
        <div className="h-64 bg-white rounded-3xl animate-pulse shadow-sm" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-rose-500 text-sm">Failed to load dashboard. Please verify the backend service.</p>
      </div>
    )
  }

  const { user, sport_breakdown, weekly_trend, heatmap, recent_activities, goal_progress } = data

  // Build a fixed Jan 1 – Dec 31 calendar for the current year.
  // This keeps the "X active days in YYYY" label correct (library uses first date's year).
  // The rolling 365-day backend data is mapped onto the fixed year range.
  const heatmapMap = new Map<string, number>()
  heatmap.forEach(h => heatmapMap.set(h.date, h.points))

  const currentYear = new Date().getFullYear()
  const calendarData: { date: string; count: number; level: 0 | 1 | 2 | 3 | 4 }[] = []
  for (let month = 0; month < 12; month++) {
    const daysInMonth = new Date(currentYear, month + 1, 0).getDate()
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${currentYear}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
      const pts = heatmapMap.get(dateStr) ?? 0
      let level: 0 | 1 | 2 | 3 | 4 = 0
      if (pts >= 1000) level = 4
      else if (pts >= 500) level = 3
      else if (pts >= 200) level = 2
      else if (pts > 0) level = 1
      calendarData.push({ date: dateStr, count: pts > 0 ? 1 : 0, level })
    }
  }

  const filteredActivities = activeSport
    ? recent_activities.filter(a => a.sport === activeSport)
    : recent_activities

  // Use backend-provided total, not the capped recent list
  const completedCount = (user as any).total_activities ?? recent_activities.length




  return (
    <div className="max-w-4xl mx-auto px-4 py-6 sm:py-8 space-y-6">

      {/* ── Top Header Greeting (Direct Reference UI match) ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">
            Hi, {user.first_name || firstName || 'Athlete'}
          </h1>
          <p className="text-sm font-semibold text-gray-500 mt-0.5">Let's check your activity</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white text-lg font-bold shadow-md shadow-violet-200">
            {user.first_name?.[0] || 'A'}
          </div>
        </div>
      </div>

      {/* ── Reference UI Stat Cards: Finished / In Progress / Time Spent ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        {/* Large Finished Card */}
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow">
          <div className="flex items-center gap-2 text-xs font-bold text-gray-500 uppercase tracking-wider">
            <span>💪</span> Finished
          </div>
          <div className="my-3">
            <span className="text-4xl font-black text-gray-900 tracking-tight tabular-nums">
              {completedCount}
            </span>
          </div>
          <div className="text-xs text-gray-400 font-semibold">
            Completed Workouts
          </div>
        </div>

        {/* In Progress Card */}
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow">
          <div className="flex items-center gap-2 text-xs font-bold text-gray-500 uppercase tracking-wider">
            <span>🐣</span> Current Streak
          </div>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-4xl font-black text-violet-600 tracking-tight tabular-nums">
              {user.streak}
            </span>
            <span className="text-xs font-bold text-gray-500">Days Active</span>
          </div>
          <div className="flex items-center gap-2">
            <TierBadge tier={user.tier as Tier} size="sm" />
            <span className="text-xs text-gray-400">Rank #{user.rank}</span>
          </div>
        </div>

        {/* Time Spent / Total Points Card */}
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow">
          <div className="flex items-center gap-2 text-xs font-bold text-gray-500 uppercase tracking-wider">
            <span>⏱</span> Total Points
          </div>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-4xl font-black text-emerald-600 tracking-tight tabular-nums">
              {user.total_points.toLocaleString()}
            </span>
            <span className="text-xs font-bold text-gray-500">pts</span>
          </div>

        </div>
      </div>

      {/* ── Tier Progress Bar Card ── */}
      {user.tier !== 'elite' && (
        <div className="bg-gradient-to-r from-violet-600 to-indigo-600 rounded-3xl p-6 text-white shadow-lg shadow-violet-200">
          <div className="flex items-center justify-between text-xs font-bold text-violet-100 mb-2">
            <span className="uppercase tracking-wider">Tier Progression</span>
            <span>{user.points_to_next_tier} pts to next tier</span>
          </div>
          <div className="h-3 bg-white/20 rounded-full overflow-hidden mb-2">
            <div
              className="h-full bg-white rounded-full transition-all duration-700"
              style={{ width: `${user.tier_progress_pct}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-xs font-medium text-violet-100">
            <span className="capitalize">Current: {user.tier}</span>
            <span>{user.tier_progress_pct}% Completed</span>
          </div>
        </div>
      )}


      {/* ── Charts: Weekly Points Trend & Sport Breakdown ── */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Weekly Trend */}
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
          <p className="text-xs font-bold text-violet-600 uppercase tracking-widest mb-1">Progress History</p>
          <h3 className="font-extrabold text-gray-900 mb-4 text-base">Weekly Points Trend</h3>
          {weekly_trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={weekly_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis
                  dataKey="week"
                  tick={{ fill: '#9ca3af', fontSize: 10 }}
                  tickFormatter={(w: string) => w.split('-W')[1] ? `W${w.split('-W')[1]}` : w}
                />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} width={35} />
                <Tooltip
                  contentStyle={{ background: '#fff', border: '1px solid #f3f4f6', borderRadius: 16, boxShadow: '0 4px 12px rgba(0,0,0,0.06)' }}
                  labelStyle={{ color: '#6b7280', fontWeight: 600 }}
                  itemStyle={{ color: '#7c3aed', fontWeight: 700 }}
                />
                <Line
                  type="monotone"
                  dataKey="points"
                  stroke="#7c3aed"
                  strokeWidth={3}
                  dot={{ fill: '#7c3aed', r: 4, strokeWidth: 2, stroke: '#ede9fe' }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex flex-col items-center justify-center text-gray-400 text-sm gap-2">
              <span className="text-3xl">📈</span>
              Log activities to unlock your trend graph
            </div>
          )}
        </div>

        {/* Sport breakdown */}
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
          <p className="text-xs font-bold text-violet-600 uppercase tracking-widest mb-1">Workout Distribution</p>
          <h3 className="font-extrabold text-gray-900 mb-4 text-base">Sport Breakdown</h3>
          {sport_breakdown.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={sport_breakdown}
                    dataKey="total_points"
                    nameKey="sport"
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={75}
                    paddingAngle={4}
                    onClick={(d) => setActiveSport(activeSport === d.sport ? null : d.sport)}
                  >
                    {sport_breakdown.map((entry) => (
                      <Cell
                        key={entry.sport}
                        fill={SPORT_COLORS[entry.sport] ?? '#9ca3af'}
                        opacity={!activeSport || activeSport === entry.sport ? 1 : 0.3}
                        cursor="pointer"
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#fff', border: '1px solid #f3f4f6', borderRadius: 16 }}
                    formatter={(v: number, name: string) => [`${v.toLocaleString()} pts`, name]}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap gap-2 mt-1 justify-center">
                {sport_breakdown.map(entry => (
                  <button
                    key={entry.sport}
                    id={`sport-filter-${entry.sport}`}
                    onClick={() => setActiveSport(activeSport === entry.sport ? null : entry.sport)}
                    className={`flex items-center gap-1 text-xs px-3 py-1 rounded-full border transition-all ${
                      activeSport && activeSport !== entry.sport ? 'opacity-30' : ''
                    }`}
                    style={{ color: SPORT_COLORS[entry.sport], borderColor: SPORT_COLORS[entry.sport] + '40', background: SPORT_COLORS[entry.sport] + '10' }}
                  >
                    <span className="w-2 h-2 rounded-full inline-block" style={{ background: SPORT_COLORS[entry.sport] }} />
                    {SPORT_EMOJI[entry.sport]} {entry.sport} {entry.percentage}%
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div className="h-48 flex flex-col items-center justify-center text-gray-400 text-sm gap-2">
              <span className="text-3xl">🥧</span>
              Log activities across sports to see breakdown
            </div>
          )}
        </div>
      </div>

      {/* ── Activity Heatmap (Yearly Calendar) ── */}
      <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
        <p className="text-xs font-bold text-violet-600 uppercase tracking-widest mb-1">Consistency Tracker</p>
        <h3 className="font-extrabold text-gray-900 mb-4 text-base">Activity Heatmap</h3>
        {calendarData.length > 0 ? (
          <div className="overflow-x-auto pb-1">
            <ActivityCalendar
              data={calendarData}
              colorScheme="light"
              theme={{
                light: ['#f3f4f6', '#ddd6fe', '#c4b5fd', '#a78bfa', '#7c3aed'],
                dark: ['#f3f4f6', '#ddd6fe', '#c4b5fd', '#a78bfa', '#7c3aed'],
              }}
              labels={{
                legend: { less: 'Less', more: 'More' },
                months: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
                weekdays: ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'],
                totalCount: '{{count}} active days in {{year}}',
              }}
              fontSize={11}
              blockSize={12}
              blockMargin={3}
              style={{ color: '#9ca3af' }}
            />
          </div>
        ) : (
          <div className="h-24 flex flex-col items-center justify-center text-gray-400 text-sm gap-1">
            <span className="text-2xl">📅</span>
            Start logging activities to see your heatmap
          </div>
        )}
      </div>

      {/* ── Recent Activities & AI Coaching Insights ── */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Recent activities */}
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs font-bold text-violet-600 uppercase tracking-widest mb-0.5">Workout Log</p>
              <h3 className="font-extrabold text-gray-900 text-base">
                Recent Activities
                {activeSport && (
                  <span className="text-violet-600 text-xs font-bold ml-2">
                    ({activeSport} <button onClick={() => setActiveSport(null)} className="text-gray-400 hover:text-red-500">×</button>)
                  </span>
                )}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => { setShowAllActivities(true); setActivityPage(0) }}
                className="text-xs text-violet-600 font-bold hover:underline"
              >
                See All →
              </button>
              <button
                onClick={() => navigate('/log')}
                className="text-xs text-violet-600 font-bold hover:underline"
              >
                + Log New
              </button>
            </div>
          </div>
          {filteredActivities.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-gray-400 gap-2">
              <span className="text-3xl">🏃‍♂️</span>
              <span className="text-sm">No activities logged yet</span>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredActivities.slice(0, 6).map(a => (
                <div key={a.id} className="flex items-center gap-3 p-3 bg-gray-50/60 rounded-2xl hover:bg-violet-50/40 transition-colors">
                  <div className="w-10 h-10 rounded-xl bg-white border border-gray-100 flex items-center justify-center text-xl shrink-0 shadow-sm">
                    {SPORT_EMOJI[a.sport] ?? '🏃'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-gray-900 truncate">
                      {a.title || `${a.sport.toUpperCase()} workout`}
                    </div>
                    <div className="text-xs text-gray-400">
                      {a.raw_value} · {formatActivityDate(a.logged_at, user.timezone)}
                    </div>
                  </div>
                  <div className="text-xs font-black text-violet-700 tabular-nums shrink-0 bg-violet-100 rounded-xl px-2.5 py-1">
                    +{a.points_awarded} pts
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Coaching Insights */}
        <InsightsPanel userId={userId} />
      </div>

      {/* ── Badges Section ── */}
      {user.badges.length > 0 && (
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
          <p className="text-xs font-bold text-amber-500 uppercase tracking-widest mb-1">Trophy Case</p>
          <h3 className="font-extrabold text-gray-900 mb-4 text-base">Earned Badges</h3>
          <div className="flex flex-wrap gap-2.5">
            {user.badges.map(badge => (
              <span
                key={badge}
                className="bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3.5 py-1.5 rounded-full font-bold shadow-sm"
              >
                {BADGE_LABELS[badge] ?? badge}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── See All Activities Slide-over Panel ── */}
      {showAllActivities && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setShowAllActivities(false)}
          />
          {/* Panel */}
          <div className="relative ml-auto w-full max-w-lg h-full bg-white shadow-2xl flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
              <div>
                <p className="text-xs font-bold text-violet-600 uppercase tracking-widest">Workout Log</p>
                <h2 className="text-xl font-extrabold text-gray-900">All Activities</h2>
                {allActivitiesData && (
                  <p className="text-xs text-gray-400 mt-0.5">{allActivitiesData.total} total workouts</p>
                )}
              </div>
              <button
                onClick={() => setShowAllActivities(false)}
                className="w-9 h-9 rounded-2xl bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-gray-500 hover:text-gray-800 transition-colors font-bold text-lg"
              >
                ✕
              </button>
            </div>

            {/* Activity list */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {loadingMore && activityPage === 0 ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-16 bg-gray-50 rounded-2xl animate-pulse" />
                  ))}
                </div>
              ) : allActivitiesData?.activities.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-2">
                  <span className="text-4xl">🏃‍♂️</span>
                  <span className="text-sm">No activities yet — go log one!</span>
                </div>
              ) : (
                <>
                  {/* Accumulated pages */}
                  {Array.from({ length: activityPage + 1 }).map((_, pageIdx) => (
                    <AllActivitiesPage
                      key={pageIdx}
                      userId={userId!}
                      page={pageIdx}
                      pageSize={PAGE_SIZE}
                      timeZone={user.timezone}
                    />
                  ))}

                  {/* Load More */}
                  {allActivitiesData && (activityPage + 1) * PAGE_SIZE < allActivitiesData.total && (
                    <button
                      onClick={() => setActivityPage(p => p + 1)}
                      disabled={loadingMore}
                      className="w-full py-3 rounded-2xl bg-violet-50 hover:bg-violet-100 text-violet-700 text-sm font-bold border border-violet-200 transition-colors mt-2"
                    >
                      {loadingMore ? 'Loading…' : `Load More (${allActivitiesData.total - (activityPage + 1) * PAGE_SIZE} remaining)`}
                    </button>
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-100">
              <button
                onClick={() => navigate('/log')}
                className="w-full py-3 rounded-2xl bg-violet-600 hover:bg-violet-700 text-white text-sm font-bold transition-colors shadow-md shadow-violet-200"
              >
                + Log New Workout
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Sub-component to render one page of activities (avoids re-fetching earlier pages)
function AllActivitiesPage({
  userId,
  page,
  pageSize,
  timeZone,
}: {
  userId: string
  page: number
  pageSize: number
  timeZone: string
}) {
  const SPORT_EMOJI: Record<string, string> = {
    running: '🏃‍♂️', walking: '🚶‍♀️', cycling: '🚴‍♂️',
    gym: '🏋️‍♂️', swimming: '🏊‍♂️', steps: '👣',
  }

  const { data } = useQuery({
    queryKey: ['all-activities', userId, page],
    queryFn: () => getActivities({ limit: pageSize, offset: page * pageSize }),
    staleTime: 30_000,
  })

  if (!data) return null

  return (
    <>
      {data.activities.map(a => (
        <div key={a.id} className="flex items-center gap-3 p-3 bg-gray-50/70 rounded-2xl hover:bg-violet-50/40 transition-colors">
          <div className="w-10 h-10 rounded-xl bg-white border border-gray-100 flex items-center justify-center text-xl shrink-0 shadow-sm">
            {SPORT_EMOJI[a.sport] ?? '🏃'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold text-gray-900 truncate">
              {a.title || `${a.sport.toUpperCase()} workout`}
            </div>
            <div className="text-xs text-gray-400">
              {a.raw_value} · {formatActivityDate(a.logged_at, timeZone)}
            </div>
          </div>
          <div className="text-xs font-black text-violet-700 tabular-nums shrink-0 bg-violet-100 rounded-xl px-2.5 py-1">
            +{a.points_awarded} pts
          </div>
        </div>
      ))}
    </>
  )
}
