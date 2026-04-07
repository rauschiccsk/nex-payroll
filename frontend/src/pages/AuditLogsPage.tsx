import { useCallback, useEffect, useState } from 'react'
import type { AuditAction, AuditLogRead } from '@/types/audit-log'
import { listAuditLogs } from '@/services/audit-log.service'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

const ACTION_LABELS: Record<AuditAction, string> = {
  CREATE: 'Vytvorenie',
  UPDATE: 'Uprava',
  DELETE: 'Zmazanie',
}

const ACTION_COLORS: Record<AuditAction, string> = {
  CREATE: 'bg-green-100 text-green-800',
  UPDATE: 'bg-blue-100 text-blue-800',
  DELETE: 'bg-red-100 text-red-800',
}

// -- Helpers -----------------------------------------------------------------
function formatDateTime(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleString('sk-SK')
}

function formatJson(data: Record<string, unknown> | null): string {
  if (!data) return '\u2014'
  return JSON.stringify(data, null, 2)
}

function truncateId(id: string): string {
  return id.length > 8 ? `${id.substring(0, 8)}...` : id
}

// -- Component ---------------------------------------------------------------
function AuditLogsPage() {
  // List state
  const [items, setItems] = useState<AuditLogRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filter state
  const [filterAction, setFilterAction] = useState<string>('')
  const [filterEntityType, setFilterEntityType] = useState<string>('')

  // Detail modal state
  const [detail, setDetail] = useState<AuditLogRead | null>(null)

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string | number> = {
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }
      if (filterAction) params.action = filterAction
      if (filterEntityType) params.entity_type = filterEntityType

      const res = await listAuditLogs(params)
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nepodarilo sa nacitat data')
    } finally {
      setLoading(false)
    }
  }, [page, filterAction, filterEntityType])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // -- Filter handlers -------------------------------------------------------
  function handleFilterChange() {
    setPage(0)
  }

  function handleActionFilter(value: string) {
    setFilterAction(value)
    handleFilterChange()
  }

  function handleEntityTypeFilter(value: string) {
    setFilterEntityType(value)
    handleFilterChange()
  }

  function clearFilters() {
    setFilterAction('')
    setFilterEntityType('')
    setPage(0)
  }

  // -- Render ----------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit log</h1>
        <p className="mt-1 text-sm text-gray-600">
          Historia zmien v systeme - vsetky operacie nad entitami
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Akcia</label>
          <select
            value={filterAction}
            onChange={(e) => handleActionFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="">Vsetky</option>
            <option value="CREATE">Vytvorenie</option>
            <option value="UPDATE">Uprava</option>
            <option value="DELETE">Zmazanie</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Typ entity</label>
          <input
            type="text"
            value={filterEntityType}
            onChange={(e) => handleEntityTypeFilter(e.target.value)}
            placeholder="napr. employees"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        {(filterAction || filterEntityType) && (
          <button
            onClick={clearFilters}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Zrusit filtre
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Datum a cas
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Akcia
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Typ entity
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                ID entity
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Pouzivatel
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                IP adresa
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Detail
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                  Nacitavam...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                  Ziadne zaznamy v audit logu
                </td>
              </tr>
            )}
            {!loading &&
              items.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDateTime(entry.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        ACTION_COLORS[entry.action as AuditAction] ?? 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {ACTION_LABELS[entry.action as AuditAction] ?? entry.action}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {entry.entity_type}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-mono text-gray-700">
                    <span title={entry.entity_id}>{truncateId(entry.entity_id)}</span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-mono text-gray-700">
                    {entry.user_id ? truncateId(entry.user_id) : '\u2014'}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {entry.ip_address ?? '\u2014'}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(entry)}
                      className="text-primary-600 hover:text-primary-800"
                    >
                      Zobrazit
                    </button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3">
            <p className="text-sm text-gray-700">
              Zobrazenych {page * PAGE_SIZE + 1}&ndash;{Math.min((page + 1) * PAGE_SIZE, total)} z{' '}
              {total}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Predchadzajuca
              </button>
              <span className="flex items-center px-2 text-sm text-gray-700">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Nasledujuca
              </button>
            </div>
          </div>
        )}
      </div>

      {/* -- Detail Modal ----------------------------------------------------- */}
      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Detail audit zaznamu</h2>
              <button
                onClick={() => setDetail(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                &times;
              </button>
            </div>

            <div className="space-y-4">
              {/* Meta info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium uppercase text-gray-500">ID</label>
                  <p className="mt-1 font-mono text-sm text-gray-900">{detail.id}</p>
                </div>
                <div>
                  <label className="block text-xs font-medium uppercase text-gray-500">
                    Datum a cas
                  </label>
                  <p className="mt-1 text-sm text-gray-900">{formatDateTime(detail.created_at)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium uppercase text-gray-500">Akcia</label>
                  <p className="mt-1">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        ACTION_COLORS[detail.action as AuditAction] ?? 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {ACTION_LABELS[detail.action as AuditAction] ?? detail.action}
                    </span>
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium uppercase text-gray-500">
                    Typ entity
                  </label>
                  <p className="mt-1 text-sm text-gray-900">{detail.entity_type}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium uppercase text-gray-500">
                    ID entity
                  </label>
                  <p className="mt-1 font-mono text-sm text-gray-900">{detail.entity_id}</p>
                </div>
                <div>
                  <label className="block text-xs font-medium uppercase text-gray-500">
                    Tenant ID
                  </label>
                  <p className="mt-1 font-mono text-sm text-gray-900">{detail.tenant_id}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium uppercase text-gray-500">
                    Pouzivatel ID
                  </label>
                  <p className="mt-1 font-mono text-sm text-gray-900">
                    {detail.user_id ?? '\u2014'}
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium uppercase text-gray-500">
                    IP adresa
                  </label>
                  <p className="mt-1 text-sm text-gray-900">{detail.ip_address ?? '\u2014'}</p>
                </div>
              </div>

              {/* Old values */}
              <div>
                <label className="block text-xs font-medium uppercase text-gray-500">
                  Povodne hodnoty
                </label>
                <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-800">
                  {formatJson(detail.old_values)}
                </pre>
              </div>

              {/* New values */}
              <div>
                <label className="block text-xs font-medium uppercase text-gray-500">
                  Nove hodnoty
                </label>
                <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-800">
                  {formatJson(detail.new_values)}
                </pre>
              </div>
            </div>

            {/* Close button */}
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setDetail(null)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zavriet
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AuditLogsPage
