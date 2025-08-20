import { createContext, useContext, useState } from 'react'

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [user, setUser] = useState({ role: 'guest' })
  const loginAs = (role) => setUser({ role })
  return (
    <AuthContext.Provider value={{ user, loginAs }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
