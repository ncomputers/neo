import { useState } from 'react'
import { apiFetch } from './api'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [pin, setPin] = useState('')

  const handleEmailLogin = async (e) => {
    e.preventDefault()
    const res = await apiFetch('/login/email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (res.ok) {
      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      // role is encoded in JWT; for demo store separately
      localStorage.setItem('role', data.role ?? '')
      window.location.href = '/dashboard'
    }
  }

  const handlePinLogin = async (e) => {
    e.preventDefault()
    const res = await apiFetch('/login/pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, pin }),
    })
    if (res.ok) {
      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('role', data.role ?? '')
      window.location.href = '/dashboard'
    }
  }

  return (
    <div className="p-4 space-y-4">
      <form onSubmit={handleEmailLogin} className="space-y-2">
        <h2 className="text-xl font-bold">Admin Login</h2>
        <input
          placeholder="Email"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="border p-1"
        />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="border p-1"
        />
        <button
          type="submit"
          aria-label="Login with email"
          className="bg-primary text-white px-2 py-1 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          Login
        </button>
      </form>
      <form onSubmit={handlePinLogin} className="space-y-2">
        <h2 className="text-xl font-bold">Staff PIN Login</h2>
        <input
          placeholder="User"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="border p-1"
        />
        <input
          placeholder="PIN"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          className="border p-1"
        />
        <button
          type="submit"
          aria-label="Login with PIN"
          className="bg-success text-white px-2 py-1 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success"
        >
          Login
        </button>
      </form>
    </div>
  )
}
