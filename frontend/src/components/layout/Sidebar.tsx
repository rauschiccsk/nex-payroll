import { useState } from 'react'
import { NavLink, useLocation } from 'react-router'

// ── Types ──────────────────────────────────────────────────
interface NavItem {
  to: string
  label: string
  icon: string
  end?: boolean
}

interface NavSection {
  title: string
  items: NavItem[]
}

// ── Navigation structure ───────────────────────────────────
const currentYear = new Date().getFullYear()

const mainSections: NavSection[] = [
  {
    title: '',
    items: [{ to: '/', label: 'Dashboard', icon: '📊', end: true }],
  },
  {
    title: 'Zamestnanci',
    items: [
      { to: '/employees', label: 'Zamestnanci', icon: '👥' },
      { to: '/contracts', label: 'Zmluvy', icon: '📄' },
      { to: '/employee-children', label: 'Deti zamestnancov', icon: '👶' },
    ],
  },
  {
    title: 'Mzdy a platby',
    items: [
      { to: '/payroll', label: 'Mzdy', icon: '💰' },
      { to: '/payslips', label: 'Výplatné pásky', icon: '🧾' },
      { to: '/payments', label: 'Platby', icon: '🏦' },
    ],
  },
  {
    title: 'Dovolenky',
    items: [
      { to: '/leaves', label: 'Dovolenky', icon: '🏖️' },
      { to: '/leaves/calendar', label: 'Kalendár', icon: '📅' },
      { to: '/leave-entitlements', label: 'Nároky', icon: '✅' },
    ],
  },
  {
    title: 'Reporting',
    items: [
      { to: '/reports', label: 'Výkazy', icon: '📈' },
      { to: `/annual/${currentYear}`, label: 'Ročné zúčtovanie', icon: '📋' },
    ],
  },
  {
    title: 'Ostatné',
    items: [
      { to: '/notifications', label: 'Notifikácie', icon: '🔔' },
      { to: '/integration/ledger', label: 'Účtovníctvo', icon: '🔗' },
    ],
  },
]

const settingsItems: NavItem[] = [
  { to: '/settings', label: 'Nastavenia', icon: '⚙️', end: true },
  { to: '/settings/users', label: 'Používatelia', icon: '👤' },
  { to: '/settings/tenants', label: 'Tenanty', icon: '🏢' },
  { to: '/settings/contribution-rates', label: 'Sadzby odvodov', icon: '📊' },
  { to: '/settings/health-insurers', label: 'Zdrav. poisťovne', icon: '🏥' },
  { to: '/settings/tax-brackets', label: 'Daňové pásma', icon: '💹' },
  { to: '/settings/statutory-deadlines', label: 'Zákonné termíny', icon: '⏰' },
  { to: '/settings/audit-logs', label: 'Audit log', icon: '📝' },
]

// ── Component ──────────────────────────────────────────────
function Sidebar() {
  const location = useLocation()
  const [settingsOpen, setSettingsOpen] = useState(
    location.pathname.startsWith('/settings'),
  )

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive
        ? 'bg-primary-50 text-primary-700'
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    }`

  const sectionTitleClass =
    'px-3 pt-4 pb-1 text-xs font-semibold uppercase tracking-wider text-gray-400'

  return (
    <aside className="flex h-full w-64 flex-shrink-0 flex-col border-r border-gray-200 bg-white">
      {/* Brand */}
      <div className="flex h-16 items-center gap-2 border-b border-gray-200 px-6">
        <span className="text-xl font-bold text-primary-600">NEX</span>
        <span className="text-xl font-light text-gray-600">Payroll</span>
      </div>

      {/* Main navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-2">
        {mainSections.map((section) => (
          <div key={section.title || '_root'}>
            {section.title && (
              <div className={sectionTitleClass}>{section.title}</div>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={linkClass}
                  end={item.end}
                >
                  <span className="w-5 text-center">{item.icon}</span>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Settings section */}
      <div className="border-t border-gray-200 px-3 py-3">
        <button
          type="button"
          onClick={() => setSettingsOpen((prev) => !prev)}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
        >
          <span className="w-5 text-center">⚙️</span>
          <span className="flex-1 text-left">Nastavenia</span>
          <span
            className={`text-xs text-gray-400 transition-transform ${settingsOpen ? 'rotate-180' : ''}`}
          >
            ▾
          </span>
        </button>

        {settingsOpen && (
          <div className="mt-1 space-y-0.5 pl-2">
            {settingsItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={linkClass}
                end={item.end}
              >
                <span className="w-5 text-center">{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}

export default Sidebar
