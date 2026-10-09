// ── Enums ──────────────────────────────────────────────────────────────────

export type SportType = 'running' | 'walking' | 'cycling' | 'gym' | 'swimming' | 'steps'
export type MetricType = 'distance_km' | 'duration_minsec' | 'count'
export type Tier = 'rookie' | 'active' | 'athlete' | 'competitor' | 'elite'

// ── User ──────────────────────────────────────────────────────────────────

export interface User {
  user_id: string
  first_name: string
  last_name: string
  email?: string
  username?: string
  total_points: number
  current_streak: number
  tier: Tier
  created_at: string
}

// ── Leaderboard ───────────────────────────────────────────────────────────

export interface LeaderboardEntry {
  rank: number
  rank_delta: number
  user_id: string
  first_name: string
  username?: string
  total_points: number
  tier: Tier
  current_streak: number
  badges: string[]
}

export interface LeaderboardResponse {
  data: LeaderboardEntry[]
  total: number
  generated_at: string
}

// ── Activity ─────────────────────────────────────────────────────────────

export interface ActivityResponse {
  activity_id: string
  points_awarded: number
  user_total_points: number
  current_streak: number
  new_badges: string[]
  is_personal_best: boolean
}

// ── Dashboard ─────────────────────────────────────────────────────────────

export interface SportBreakdown {
  sport: SportType
  total_points: number
  percentage: number
}

export interface WeeklyTrend {
  week: string
  points: number
}

export interface HeatmapEntry {
  date: string
  points: number
}

export interface GoalProgress {
  target: number
  achieved: number
  percentage: number
}

export interface DashboardUser {
  first_name: string
  last_name: string
  username?: string
  total_points: number
  rank: number
  tier: Tier
  tier_emoji: string
  tier_progress_pct: number
  points_to_next_tier: number
  streak: number
  badges: string[]
}

export interface DashboardData {
  user: DashboardUser
  sport_breakdown: SportBreakdown[]
  weekly_trend: WeeklyTrend[]
  heatmap: HeatmapEntry[]
  recent_activities: RecentActivity[]
  goal_progress?: GoalProgress
}

export interface RecentActivity {
  id: string
  sport: SportType
  metric_type: MetricType
  raw_value: string
  points_awarded: number
  title?: string
  logged_at: string
  source: string
}

// ── Insights ──────────────────────────────────────────────────────────────

export interface Insight {
  icon: string
  title: string
  text: string
}

// ── Challenges ────────────────────────────────────────────────────────────

export interface DailyChallenge {
  title: string
  description: string
  sport: SportType
  metric: { type: MetricType; target: number | string }
  bonus_points: number
  difficulty: 'easy' | 'medium' | 'hard'
  coach_note: string
  // Added when the challenge is persisted to DB
  challenge_id?: string
  my_progress?: number
  my_status?: 'accepted' | 'completed'
}

export interface ChallengeParticipantInfo {
  user_id: string
  first_name: string
  username?: string | null
  status: 'invited' | 'accepted' | 'declined' | 'completed'
  progress: number
  completed_at?: string | null
}

export interface UserChallenge {
  id: string
  title: string
  description?: string | null
  sport?: string | null
  metric_type: string
  target_value: number
  bonus_points: number
  difficulty: 'easy' | 'medium' | 'hard'
  creator_id?: string | null
  creator_name: string
  creator_username?: string | null
  is_creator: boolean
  my_status: 'invited' | 'accepted' | 'declined' | 'completed' | 'none'
  my_progress: number
  start_date?: string | null
  end_date?: string | null
  created_at?: string | null
  is_daily?: boolean
  participants: ChallengeParticipantInfo[]
}

// ── WebSocket ─────────────────────────────────────────────────────────────

export interface WsMessage {
  event: string
  data: Record<string, unknown>
}
