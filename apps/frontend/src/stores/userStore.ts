import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

interface UserState {
  userId: string | null
  firstName: string | null
  username: string | null
  token: string | null
  totalPoints: number
  setUser: (
    id: string,
    name: string,
    points: number,
    token?: string | null,
    username?: string | null
  ) => void
  setUsername: (username: string | null) => void
  setToken: (token: string | null) => void
  updatePoints: (points: number) => void
  clearUser: () => void
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      userId: null,
      firstName: null,
      username: null,
      token: null,
      totalPoints: 0,
      setUser: (id, name, points, token = null, username = null) => {
        set((state) => ({
          userId: id,
          firstName: name,
          totalPoints: points,
          token: token !== undefined && token !== null ? token : state.token,
          username: username !== undefined && username !== null ? username : state.username,
        }))
      },
      setUsername: (username) => set({ username }),
      setToken: (token) => set({ token }),
      updatePoints: (points) => set({ totalPoints: points }),
      clearUser: () => {
        set({ userId: null, firstName: null, username: null, token: null, totalPoints: 0 })
      },
    }),
    {
      name: 'fitness-user',
      storage: createJSONStorage(() => localStorage),
    }
  )
)
