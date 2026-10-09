import { useEffect } from 'react'
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import { useUserStore } from './stores/userStore'
import { logoutUser, getCurrentUser } from './api/endpoints'
import RegisterPage from './pages/RegisterPage'
import LeaderboardPage from './pages/LeaderboardPage'
import DashboardPage from './pages/DashboardPage'
import LogActivityPage from './pages/LogActivityPage'
import ChallengesPage from './pages/ChallengesPage'
import FriendsPage from './pages/FriendsPage'

const NAV_ITEMS = [
  { to: '/',           label: 'Leaderboard', icon: '🏆' },
  { to: '/dashboard',  label: 'Dashboard',   icon: '📊' },
  { to: '/log',        label: 'Log',         icon: '➕' },
  { to: '/challenges', label: 'Challenges',  icon: '🎯' },
  { to: '/friends',    label: 'Friends',     icon: '👥' },
]

function NavBar() {
  const firstName = useUserStore(s => s.firstName)
  const username = useUserStore(s => s.username)
  const totalPoints = useUserStore(s => s.totalPoints)
  const clearUser = useUserStore(s => s.clearUser)
  const navigate = useNavigate()

  return (
    <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-gray-100 shadow-sm">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center gap-4">
        {/* Brand */}
        <NavLink to="/" className="flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 rounded-xl bg-violet-600 flex items-center justify-center text-white text-sm font-bold shadow-md shadow-violet-200">
            🏃
          </div>
          <span className="font-bold text-gray-900 text-base hidden sm:block">FitChallenge</span>
        </NavLink>

        {/* Desktop Nav links */}
        <nav className="hidden md:flex items-center gap-1 flex-1 ml-2">
          {NAV_ITEMS.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-1.5 ${
                  isActive
                    ? 'bg-violet-100 text-violet-700 font-semibold'
                    : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User info */}
        <div className="ml-auto flex items-center gap-3">
          {firstName ? (
            <>
              <div className="hidden sm:flex flex-col items-end">
                <span className="text-sm font-semibold text-gray-800 flex items-center gap-1">
                  {firstName}
                  {username && <span className="text-violet-500 font-mono text-xs">(@{username})</span>}
                </span>
                <span className="text-xs text-gray-400">{totalPoints.toLocaleString()} pts</span>
              </div>
              {/* Avatar circle */}
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-700 flex items-center justify-center text-white text-sm font-bold shadow">
                {firstName[0]}
              </div>
              <button
                onClick={async () => {
                  try { await logoutUser() } catch { /* ignore */ }
                  clearUser()
                  navigate('/register')
                }}
                className="text-xs text-gray-400 hover:text-gray-700 transition-colors ml-1"
              >
                Sign out
              </button>
            </>
          ) : (
            <NavLink
              to="/register"
              className="btn-primary !py-1.5 !px-4 !text-sm !rounded-xl !shadow-md !shadow-violet-200"
            >
              Get Started
            </NavLink>
          )}
        </div>
      </div>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 shadow-[0_-4px_20px_rgba(0,0,0,0.06)] flex z-50 pb-safe">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center py-2.5 text-[10px] font-medium transition-all duration-200 gap-0.5 ${
                isActive ? 'text-violet-600' : 'text-gray-400'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <div className={`w-10 h-7 flex items-center justify-center rounded-xl transition-all duration-200 ${
                  isActive ? 'bg-violet-100' : ''
                }`}>
                  <span className="text-lg leading-none">{item.icon}</span>
                </div>
                <span className="mt-0.5">{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </header>
  )
}

export default function App() {
  const setUser = useUserStore(s => s.setUser)
  const clearUser = useUserStore(s => s.clearUser)

  useEffect(() => {
    const token = useUserStore.getState().token
    if (token) {
      getCurrentUser()
        .then((user) => {
          setUser(user.user_id, user.first_name, user.total_points, token, user.username)
        })
        .catch((err) => {
          if (err.response?.status === 401) {
            clearUser()
          }
        })
    }
  }, [setUser, clearUser])

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #f0f0f9 0%, #f7f7fc 50%, #ede9fe10 100%)' }}>
      <NavBar />
      {/* Extra bottom padding on mobile for the fixed nav bar */}
      <main className="pb-24 md:pb-6">
        <Routes>
          <Route path="/"           element={<LeaderboardPage />} />
          <Route path="/register"   element={<RegisterPage />} />
          <Route path="/dashboard"  element={<DashboardPage />} />
          <Route path="/log"        element={<LogActivityPage />} />
          <Route path="/challenges" element={<ChallengesPage />} />
          <Route path="/friends"    element={<FriendsPage />} />
        </Routes>
      </main>
    </div>
  )
}
