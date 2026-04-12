import { useState, useRef, useEffect } from 'react'

/**
 * TenantSelector — tenant switching dropdown.
 * Placeholder: will be wired to tenantStore + API in later phases.
 */
function TenantSelector() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
      >
        <span className="w-4 text-center">🏢</span>
        <span>Tenant</span>
        <span
          className={`text-xs text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
        >
          ▾
        </span>
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
          <p className="px-3 py-2 text-xs text-gray-400">
            Tenant switching will be available after API integration.
          </p>
        </div>
      )}
    </div>
  )
}

export default TenantSelector
