import { NavLink } from 'react-router'

interface NavItem {
  to: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: '📊' },
  { to: '/employees', label: 'Zamestnanci', icon: '👥' },
  { to: '/contracts', label: 'Zmluvy', icon: '📄' },
  { to: '/payroll', label: 'Mzdy', icon: '💰' },
  { to: '/leaves', label: 'Dovolenky', icon: '🏖️' },
  { to: '/reports', label: 'Výkazy', icon: '📈' },
  { to: '/payments', label: 'Platby', icon: '🏦' },
]

const secondaryItems: NavItem[] = [
  { to: '/settings', label: 'Nastavenia', icon: '⚙️' },
]

function Sidebar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive
        ? 'bg-primary-50 text-primary-700'
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    }`

  return (
    <aside className="flex h-full w-64 flex-col border-r border-gray-200 bg-white">
      <div className="flex h-16 items-center gap-2 border-b border-gray-200 px-6">
        <span className="text-xl font-bold text-primary-600">NEX</span>
        <span className="text-xl font-light text-gray-600">Payroll</span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} className={linkClass} end={item.to === '/'}>
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-gray-200 px-3 py-4 space-y-1">
        {secondaryItems.map((item) => (
          <NavLink key={item.to} to={item.to} className={linkClass}>
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>
    </aside>
  )
}

export default Sidebar
