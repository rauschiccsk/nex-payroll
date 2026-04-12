import { useNavigate } from 'react-router'
import { useSyncExternalStore } from 'react'
import { authStore } from '@/stores/auth.store'
import TenantSelector from './TenantSelector'
import NotificationBell from './NotificationBell'

const ROLE_LABELS: Record<string, string> = {
  director: 'Riaditeľ',
  accountant: 'Účtovník',
  employee: 'Zamestnanec',
}

/**
 * Header — TenantSelector, user display (name+role), NotificationBell, logout.
 */
function Header() {
  const navigate = useNavigate()
  const currentUser = useSyncExternalStore(
    authStore.subscribe,
    () => authStore.getState().currentUser,
  )

  function handleLogout() {
    authStore.getState().clear()
    navigate('/login')
  }

  const displayName = currentUser?.username ?? 'User'
  const displayRole = currentUser?.role ? (ROLE_LABELS[currentUser.role] ?? currentUser.role) : 'N/A'
  const initials = displayName.charAt(0).toUpperCase()

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div className="flex items-center gap-4">
        <TenantSelector />
      </div>

      <div className="flex items-center gap-3">
        <NotificationBell />

        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-sm font-medium text-primary-700">
            {initials}
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium leading-tight text-gray-700">
              {displayName}
            </span>
            <span className="text-xs leading-tight text-gray-400">
              {displayRole}
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="ml-2 rounded-lg px-3 py-1.5 text-sm text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
          aria-label="Logout"
        >
          Odhlásiť
        </button>
      </div>
    </header>
  )
}

export default Header
