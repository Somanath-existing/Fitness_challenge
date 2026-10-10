import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { registerUser, loginUser } from '../api/endpoints'
import { useUserStore } from '../stores/userStore'

const detectedTz = typeof Intl !== 'undefined' ? Intl.DateTimeFormat().resolvedOptions().timeZone : 'UTC'

export default function RegisterPage() {
  const navigate = useNavigate()
  const setUser = useUserStore((s) => s.setUser)
  const [mode, setMode] = useState<'register' | 'login'>('login')

  // Register form state
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    username: '',
    password: '',
    timezone: detectedTz || 'UTC',
    fitness_goal: '',
    bio: '',
  })

  // Login form state
  const [loginForm, setLoginForm] = useState({
    identifier: '',
    password: '',
  })

  const [error, setError] = useState('')
  const [showLoginPassword, setShowLoginPassword] = useState(false)
  const [showRegPassword, setShowRegPassword] = useState(false)

  const registerMutation = useMutation({
    mutationFn: () =>
      registerUser({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email || undefined,
        username: form.username || undefined,
        password: form.password || undefined,
        timezone: form.timezone,
        fitness_goal: form.fitness_goal ? Number(form.fitness_goal) : undefined,
        bio: form.bio || undefined,
      }),
    onSuccess: async (data) => {
      if (form.password && (form.username || form.email)) {
        try {
          const authRes = await loginUser({
            identifier: form.username || form.email,
            password: form.password,
          })
          setUser(
            authRes.user.user_id,
            authRes.user.first_name,
            authRes.user.total_points,
            authRes.access_token,
            authRes.user.username
          )
          navigate('/')
          return
        } catch {
          // Fall through to registration response
        }
      }

      setUser(data.user_id, data.first_name, 0, undefined, form.username || undefined)
      navigate('/')
    },
    onError: (err: Error) => {
      setError(err.message)
    },
  })

  const loginMutation = useMutation({
    mutationFn: () =>
      loginUser({
        identifier: loginForm.identifier.trim(),
        password: loginForm.password,
      }),
    onSuccess: (data) => {
      setUser(
        data.user.user_id,
        data.user.first_name,
        data.user.total_points,
        data.access_token,
        data.user.username
      )
      navigate('/')
    },
    onError: (err: Error) => {
      setError(err.message)
    },
  })

  const handleRegisterSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.first_name.trim() || !form.last_name.trim()) {
      setError('First and last name are required.')
      return
    }
    if (form.password) {
      if (form.password.length < 8) {
        setError('Password must be at least 8 characters.')
        return
      }
      if (!/[A-Z]/.test(form.password)) {
        setError('Password must contain at least one uppercase letter.')
        return
      }
      if (!/[0-9]/.test(form.password)) {
        setError('Password must contain at least one number.')
        return
      }
      if (!/[^A-Za-z0-9]/.test(form.password)) {
        setError('Password must contain at least one special character (e.g. @, #, !).')
        return
      }
    }
    registerMutation.mutate()
  }

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!loginForm.identifier.trim() || !loginForm.password) {
      setError('Please provide username/email and password.')
      return
    }
    loginMutation.mutate()
  }

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header Branding */}
        <div className="mb-7 text-center">
          <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center text-3xl shadow-lg shadow-violet-200 mx-auto mb-3 text-white">
            🏃
          </div>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">FitChallenge</h1>
          <p className="text-gray-500 text-sm mt-1">Track workouts, compete with friends, reach your goals</p>
        </div>

        {/* Mode Switch Pills */}
        <div className="flex bg-white border border-gray-100 p-1.5 rounded-2xl mb-6 shadow-sm">
          <button
            type="button"
            id="tab-signin"
            onClick={() => { setMode('login'); setError('') }}
            className={`flex-1 py-2.5 text-sm font-bold rounded-xl transition-all duration-200 ${
              mode === 'login'
                ? 'bg-violet-600 text-white shadow-md shadow-violet-200'
                : 'text-gray-500 hover:text-gray-800'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            id="tab-register"
            onClick={() => { setMode('register'); setError('') }}
            className={`flex-1 py-2.5 text-sm font-bold rounded-xl transition-all duration-200 ${
              mode === 'register'
                ? 'bg-violet-600 text-white shadow-md shadow-violet-200'
                : 'text-gray-500 hover:text-gray-800'
            }`}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-2xl px-4 py-3 text-sm mb-4 flex items-center gap-2">
            <span>⚠️</span>
            <span className="font-medium">{error}</span>
          </div>
        )}

        {/* ── Login Form ─────────────────────────────────────────────────── */}
        {mode === 'login' ? (
          <form
            onSubmit={handleLoginSubmit}
            autoComplete="off"
            className="bg-white rounded-3xl p-7 sm:p-8 border border-gray-100 shadow-sm space-y-4"
          >
            <div>
              <h2 className="text-xl font-bold text-gray-900">Welcome Back</h2>
              <p className="text-xs text-gray-500 mt-0.5">Enter your credentials to continue your streak</p>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">
                Username or Email
              </label>
              <input
                id="login-identifier"
                autoComplete="off"
                className="fit-input !py-3"
                placeholder="Your username or email"
                value={loginForm.identifier}
                onChange={(e) => setLoginForm({ ...loginForm, identifier: e.target.value })}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showLoginPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  className="fit-input !py-3 !pr-11"
                  placeholder="••••••••"
                  value={loginForm.password}
                  onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                  required
                />
                <button
                  type="button"
                  id="login-toggle-password"
                  onClick={() => setShowLoginPassword((v) => !v)}
                  className="absolute inset-y-0 right-3 flex items-center text-gray-400 hover:text-violet-600 transition-colors"
                  aria-label={showLoginPassword ? 'Hide password' : 'Show password'}
                >
                  {showLoginPassword ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <button
              id="login-submit-btn"
              type="submit"
              disabled={loginMutation.isPending}
              className="w-full btn-primary !rounded-2xl !py-3.5 mt-2"
            >
              {loginMutation.isPending ? 'Signing in…' : 'Sign In'}
            </button>


          </form>
        ) : (
          /* ── Registration Form ─────────────────────────────────────────── */
          <form
            onSubmit={handleRegisterSubmit}
            className="bg-white rounded-3xl p-7 sm:p-8 border border-gray-100 shadow-sm space-y-4"
          >
            <div>
              <h2 className="text-xl font-bold text-gray-900">Create Profile</h2>
              <p className="text-xs text-gray-500 mt-0.5">Join the fitness leaderboard today</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">First name *</label>
                <input
                  id="reg-firstname"
                  className="fit-input !py-2.5"
                  placeholder="Jane"
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  required
                  maxLength={50}
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Last name *</label>
                <input
                  id="reg-lastname"
                  className="fit-input !py-2.5"
                  placeholder="Doe"
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  required
                  maxLength={50}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Email</label>
              <input
                id="reg-email"
                type="email"
                className="fit-input !py-2.5"
                placeholder="jane@example.com"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Username (Handle)</label>
              <input
                id="reg-username"
                className="fit-input !py-2.5 font-mono"
                placeholder="jane_fitness"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value.toLowerCase() })}
                pattern="[a-z0-9_]+"
                minLength={3}
                maxLength={30}
              />
              <p className="text-[11px] text-gray-400 mt-1">Letters, numbers, underscores</p>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Password</label>
              <div className="relative">
                <input
                  id="reg-password"
                  type={showRegPassword ? 'text' : 'password'}
                  className="fit-input !py-2.5 !pr-11"
                  placeholder="•••••••• (min 8 chars, 1 number & 1 symbol)"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  minLength={8}
                />
                <button
                  type="button"
                  id="reg-toggle-password"
                  onClick={() => setShowRegPassword((v) => !v)}
                  className="absolute inset-y-0 right-3 flex items-center text-gray-400 hover:text-violet-600 transition-colors"
                  aria-label={showRegPassword ? 'Hide password' : 'Show password'}
                >
                  {showRegPassword ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Weekly points goal</label>
              <input
                id="reg-goal"
                type="number"
                min={1}
                className="fit-input !py-2.5"
                placeholder="500"
                value={form.fitness_goal}
                onChange={(e) => setForm({ ...form, fitness_goal: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Bio</label>
              <textarea
                id="reg-bio"
                className="fit-input !py-2 resize-none"
                placeholder="Running towards new personal records"
                value={form.bio}
                onChange={(e) => setForm({ ...form, bio: e.target.value })}
                maxLength={160}
                rows={2}
              />
            </div>

            <button
              id="register-submit-btn"
              type="submit"
              disabled={registerMutation.isPending}
              className="w-full btn-primary !rounded-2xl !py-3.5 mt-2"
            >
              {registerMutation.isPending ? 'Creating Account…' : 'Create Account'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
