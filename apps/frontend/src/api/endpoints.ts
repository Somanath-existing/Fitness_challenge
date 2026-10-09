import api from './client'
import type {
  User, LeaderboardResponse, ActivityResponse,
  DashboardData, Insight, DailyChallenge, UserChallenge,
} from '../types'

// ── Users & Auth ──────────────────────────────────────────────────────────

export const registerUser = async (data: {
  first_name: string
  last_name: string
  email?: string
  username?: string
  password?: string
  timezone?: string
  fitness_goal?: number
  bio?: string
}): Promise<User> => {
  const r = await api.post('/users', data)
  return r.data
}

export const loginUser = async (data: {
  username?: string
  email?: string
  identifier?: string
  password: string
}): Promise<{ access_token: string; token_type: string; expires_in: number; user: User }> => {
  const r = await api.post('/auth/login', data)
  return r.data
}

export const logoutUser = async (): Promise<void> => {
  await api.post('/auth/logout')
}

export const getCurrentUser = async (): Promise<User> => {
  const r = await api.get('/auth/me')
  return r.data
}

export const getUser = async (userId: string): Promise<User> => {
  const r = await api.get(`/users/${userId}`)
  return r.data
}

// ── Leaderboard ───────────────────────────────────────────────────────────

export const getLeaderboard = async (params?: {
  limit?: number
  offset?: number
  tier?: string
  scope?: 'global' | 'friends'
  user_id?: string
}): Promise<LeaderboardResponse> => {
  const r = await api.get('/leaderboard', { params })
  return r.data
}

// ── Activities ────────────────────────────────────────────────────────────

export const logActivity = async (data: {
  // user_id intentionally omitted — server uses JWT identity
  sport: string
  metric: { type: string; value: string | number }
  title?: string
  notes?: string
  location?: string
  source?: string
  logged_at?: string
}): Promise<ActivityResponse> => {
  const r = await api.post('/activities', data)
  return r.data
}

// ── Dashboard ─────────────────────────────────────────────────────────────

export const getDashboard = async (userId: string): Promise<DashboardData> => {
  // userId is the authenticated user's ID — server enforces ownership
  const r = await api.get(`/users/${userId}/dashboard`)
  return r.data
}

export const getFriendProfile = async (userId: string): Promise<DashboardData> => {
  // Calls /profile endpoint — server validates accepted friendship before returning data
  const r = await api.get(`/users/${userId}/profile`)
  return r.data
}

// ── Insights ──────────────────────────────────────────────────────────────

export const getInsights = async (userId: string): Promise<{ insights: Insight[]; cached_at: string }> => {
  const r = await api.get(`/users/${userId}/insights`)
  return r.data
}

// ── Challenges ────────────────────────────────────────────────────────────

export const getDailyChallenge = async (userId: string): Promise<DailyChallenge> => {
  const r = await api.get(`/challenges/daily/${userId}`)
  return r.data
}

export const getChallenges = async (): Promise<{ challenges: UserChallenge[]; count: number }> => {
  // No user_id param — server returns challenges for the authenticated user
  const r = await api.get('/challenges')
  return r.data
}

export const createChallenge = async (data: {
  title: string
  description?: string
  sport?: string
  metric_type: string
  target_value: number
  bonus_points: number
  difficulty: string
  end_date?: string
  invitee_ids?: string[]
  // creator_id intentionally omitted — server uses JWT identity
}): Promise<{ challenge_id: string; title: string; invited_count: number; invited_users: any[] }> => {
  const r = await api.post('/challenges', data)
  return r.data
}

export const respondChallenge = async (
  challengeId: string,
  action: 'accept' | 'decline',
): Promise<{ message: string; status: string; challenge_id: string }> => {
  // user_id param removed — server uses JWT
  const r = await api.post(`/challenges/${challengeId}/respond`, { action })
  return r.data
}

// ── Friends ───────────────────────────────────────────────────────────────

export const sendFriendRequest = async (identifier: string) => {
  // requester_id removed — server uses JWT identity
  const r = await api.post('/friends/request', { identifier: identifier.trim() })
  return r.data
}

export const getFriends = async () => {
  // user_id removed — server returns friends for the authenticated user
  const r = await api.get('/friends')
  return r.data
}

export const getFriendRequests = async () => {
  // user_id removed — server returns requests for the authenticated user
  const r = await api.get('/friends/requests')
  return r.data
}

export const respondFriendRequest = async (friendshipId: string, action: 'accept' | 'decline') => {
  // user_id removed — server uses JWT
  const r = await api.post(`/friends/${friendshipId}/respond`, { action })
  return r.data
}

export const unfriendUser = async (friendshipId: string) => {
  // user_id removed — server uses JWT
  await api.delete(`/friends/${friendshipId}`)
}

export const cancelFriendRequest = async (
  options: { friendshipId?: string; targetId?: string }
) => {
  const params: Record<string, string> = {}
  if (options.friendshipId) params.friendship_id = options.friendshipId
  if (options.targetId) params.target_id = options.targetId
  const r = await api.delete('/friends/request/cancel', { params })
  return r.data
}

export const getUserPublicProfile = async (userId: string): Promise<User> => {
  const r = await api.get(`/users/${userId}`)
  return r.data
}

export const deleteChallenge = async (challengeId: string) => {
  // user_id removed — server uses JWT
  await api.delete(`/challenges/${challengeId}`)
}
