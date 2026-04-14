import { useState, type FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router'
import { useSyncExternalStore } from 'react'
import { authStore } from '@/stores/auth.store'
import authService from '@/services/auth.service'

/**
 * LoginPage — OAuth2 password-flow login form.
 * Redirects authenticated users to dashboard.
 * After login, fetches /auth/me and redirects to the originally requested page.
 */
function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()

  const token = useSyncExternalStore(
    authStore.subscribe,
    () => authStore.getState().token,
  )

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // If already authenticated, redirect to dashboard (or original target)
  const from = (location.state as { from?: string } | null)?.from ?? '/'
  if (token) {
    navigate(from, { replace: true })
    return null
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await authService.login({ username, password })
      // Fetch user info to populate store (tenant_id, role, etc.)
      const userInfo = await authService.me()
      authStore.getState().setCurrentUser({
        id: userInfo.id,
        email: userInfo.email,
        username: userInfo.username,
        role: userInfo.role as 'director' | 'accountant' | 'employee',
        tenant_id: userInfo.tenant_id,
        is_active: userInfo.is_active,
      })
      navigate(from, { replace: true })
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Prihlásenie zlyhalo'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
        <h1 className="text-2xl font-bold text-gray-900">Prihlásenie</h1>
        <p className="mt-2 text-gray-600">NEX Payroll — mzdový systém</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {error && (
            <div
              role="alert"
              className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
            >
              {error}
            </div>
          )}

          <div>
            <label
              htmlFor="username"
              className="block text-sm font-medium text-gray-700"
            >
              Používateľské meno
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              autoComplete="username"
              disabled={loading}
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700"
            >
              Heslo
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              autoComplete="current-password"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Prihlasujem...' : 'Prihlásiť sa'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginPage
