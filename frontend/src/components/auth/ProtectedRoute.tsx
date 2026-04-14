import { Navigate, useLocation } from 'react-router'
import { useSyncExternalStore } from 'react'
import { authStore } from '@/stores/auth.store'

/**
 * ProtectedRoute — redirects unauthenticated users to /login.
 * Preserves the attempted URL via `state.from` so LoginPage can
 * redirect back after successful authentication.
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const token = useSyncExternalStore(
    authStore.subscribe,
    () => authStore.getState().token,
  )

  if (!token) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  return <>{children}</>
}

export default ProtectedRoute
