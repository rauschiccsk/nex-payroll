import { useCallback, useEffect, useState } from 'react'
import type {
  LeaveEntitlementRead,
  LeaveEntitlementCreate,
  LeaveEntitlementUpdate,
} from '@/types/leave-entitlement'
import type { EmployeeRead } from '@/types/employee'
import {
  listLeaveEntitlements,
  createLeaveEntitlement,
  updateLeaveEntitlement,
  deleteLeaveEntitlement,
} from '@/services/leave-entitlement.service'
import { listEmployees } from '@/services/employee.service'
import { authStore } from '@/stores/auth.store'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

// -- Empty form state --------------------------------------------------------
interface FormState {
  tenant_id: string
  employee_id: string
  year: string
  total_days: string
  used_days: string
  remaining_days: string
  carryover_days: string
}

const EMPTY_FORM: FormState = {
  tenant_id: '',
  employee_id: '',
  year: String(new Date().getFullYear()),
  total_days: '20',
  used_days: '0',
  remaining_days: '20',
  carryover_days: '0',
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): LeaveEntitlementCreate {
  return {
    tenant_id: form.tenant_id,
    employee_id: form.employee_id,
    year: Number(form.year),
    total_days: Number(form.total_days),
    used_days: Number(form.used_days),
    remaining_days: Number(form.remaining_days),
    carryover_days: Number(form.carryover_days),
  }
}

function toUpdatePayload(form: FormState): LeaveEntitlementUpdate {
  return {
    total_days: Number(form.total_days),
    used_days: Number(form.used_days),
    remaining_days: Number(form.remaining_days),
    carryover_days: Number(form.carryover_days),
  }
}

function entitlementToForm(e: LeaveEntitlementRead): FormState {
  return {
    tenant_id: e.tenant_id,
    employee_id: e.employee_id,
    year: String(e.year),
    total_days: String(e.total_days),
    used_days: String(e.used_days),
    remaining_days: String(e.remaining_days),
    carryover_days: String(e.carryover_days),
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('sk-SK')
}

// -- Component ---------------------------------------------------------------
function LeaveEntitlementsPage() {
  // List state
  const [items, setItems] = useState<LeaveEntitlementRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail state
  const [detail, setDetail] = useState<LeaveEntitlementRead | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<LeaveEntitlementRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<LeaveEntitlementRead | null>(null)

  // Employees for dropdown
  const [employees, setEmployees] = useState<EmployeeRead[]>([])

  // -- Fetch -----------------------------------------------------------------
  useEffect(() => {
    listEmployees({ skip: 0, limit: 1000 })
      .then((res) => setEmployees(res.items))
      .catch(() => {
        /* silently ignore – dropdown will be empty */
      })
  }, [])

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listLeaveEntitlements({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nepodarilo sa načítať dáta')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // -- Modal handlers --------------------------------------------------------
  function openCreate() {
    setEditing(null)
    const tenantId = authStore.getState().tenantId ?? ''
    setForm({ ...EMPTY_FORM, tenant_id: tenantId })
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(ent: LeaveEntitlementRead) {
    setEditing(ent)
    setForm(entitlementToForm(ent))
    setFormError(null)
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setEditing(null)
    setFormError(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setFormError(null)
    try {
      if (editing) {
        await updateLeaveEntitlement(editing.id, toUpdatePayload(form))
      } else {
        await createLeaveEntitlement(toCreatePayload(form))
      }
      closeModal()
      await fetchData()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Chyba pri ukladaní')
    } finally {
      setSubmitting(false)
    }
  }

  // -- Delete handlers -------------------------------------------------------
  async function handleDelete() {
    if (!deleting) return
    try {
      await deleteLeaveEntitlement(deleting.id)
      setDeleting(null)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri mazaní')
      setDeleting(null)
    }
  }

  // -- Form field updater ----------------------------------------------------
  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => {
      const next = { ...prev, [key]: value }
      if (key === 'total_days' || key === 'used_days') {
        next.remaining_days = String(Number(next.total_days) - Number(next.used_days))
      }
      return next
    })
  }

  // -- Helper: find employee name by ID --------------------------------------
  function employeeName(employeeId: string): string {
    const emp = employees.find((e) => e.id === employeeId)
    if (emp) return `${emp.last_name} ${emp.first_name}`
    return employeeId.slice(0, 8) + '...'
  }

  // -- Render ----------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Nároky na dovolenku</h1>
          <p className="mt-1 text-sm text-gray-600">
            Evidencia nárokov na dovolenku zamestnancov podľa rokov
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nový nárok
        </button>
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
                Zamestnanec
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Rok
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Celkové dni
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Čerpané
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Zostávajúce
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Prenos
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Akcie
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                  Načítavam...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                  Žiadne záznamy
                </td>
              </tr>
            )}
            {!loading &&
              items.map((ent) => (
                <tr key={ent.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {employeeName(ent.employee_id)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">{ent.year}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                    {ent.total_days}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                    {ent.used_days}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        ent.remaining_days > 0
                          ? 'bg-green-100 text-green-800'
                          : ent.remaining_days === 0
                            ? 'bg-gray-100 text-gray-600'
                            : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {ent.remaining_days}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                    {ent.carryover_days}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(ent)}
                      className="mr-2 text-gray-600 hover:text-gray-800"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(ent)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upraviť
                    </button>
                    <button
                      onClick={() => setDeleting(ent)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Zmazať
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
              Zobrazených {page * PAGE_SIZE + 1}&ndash;
              {Math.min((page + 1) * PAGE_SIZE, total)} z {total}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Predchádzajúca
              </button>
              <span className="flex items-center px-2 text-sm text-gray-700">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Nasledujúca
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
              <h2 className="text-lg font-semibold text-gray-900">
                Nárok na dovolenku — {employeeName(detail.employee_id)} ({detail.year})
              </h2>
            </div>

            <div className="space-y-4">
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Zamestnanec</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Zamestnanec</dt>
                    <dd className="font-medium text-gray-900">
                      {employeeName(detail.employee_id)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Rok</dt>
                    <dd className="font-medium text-gray-900">{detail.year}</dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Dni dovolenky</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Celkové dni</dt>
                    <dd className="font-medium text-gray-900">{detail.total_days}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Čerpané dni</dt>
                    <dd className="font-medium text-gray-900">{detail.used_days}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Zostávajúce dni</dt>
                    <dd className="font-medium text-gray-900">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          detail.remaining_days > 0
                            ? 'bg-green-100 text-green-800'
                            : detail.remaining_days === 0
                              ? 'bg-gray-100 text-gray-600'
                              : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {detail.remaining_days}
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Prenos z predchádzajúceho roka</dt>
                    <dd className="font-medium text-gray-900">{detail.carryover_days}</dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Systém</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Vytvorené</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.created_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Aktualizované</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.updated_at)}</dd>
                  </div>
                </dl>
              </fieldset>
            </div>

            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => {
                  openEdit(detail)
                  setDetail(null)
                }}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                Upraviť
              </button>
              <button
                onClick={() => setDetail(null)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zavrieť
              </button>
            </div>
          </div>
        </div>
      )}

      {/* -- Create/Edit Modal ------------------------------------------------ */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              {editing ? 'Upraviť nárok' : 'Nový nárok na dovolenku'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Employee — only for create */}
              {!editing && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Zamestnanec
                  </label>
                  <select
                    required
                    value={form.employee_id}
                    onChange={(e) => updateField('employee_id', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    <option value="">— Vyberte zamestnanca —</option>
                    {employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.last_name} {emp.first_name} ({emp.employee_number})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Year — only for create */}
              {!editing && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Rok</label>
                  <input
                    type="number"
                    required
                    min={2000}
                    max={2100}
                    value={form.year}
                    onChange={(e) => updateField('year', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              )}

              {/* Days fields */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Celkové dni
                  </label>
                  <input
                    type="number"
                    required
                    min={0}
                    max={365}
                    value={form.total_days}
                    onChange={(e) => updateField('total_days', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Čerpané dni
                  </label>
                  <input
                    type="number"
                    required
                    min={0}
                    max={365}
                    value={form.used_days}
                    onChange={(e) => updateField('used_days', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Zostávajúce dni
                  </label>
                  <input
                    type="number"
                    required
                    readOnly
                    tabIndex={-1}
                    value={form.remaining_days}
                    className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Prenos z predchádzajúceho roka
                  </label>
                  <input
                    type="number"
                    required
                    min={0}
                    max={365}
                    value={form.carryover_days}
                    onChange={(e) => updateField('carryover_days', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Zrušiť
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {submitting
                    ? 'Ukladám...'
                    : editing
                      ? 'Uložiť zmeny'
                      : 'Vytvoriť'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* -- Delete Confirmation ---------------------------------------------- */}
      {deleting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">Potvrdiť zmazanie</h2>
            <p className="mb-4 text-sm text-gray-600">
              Naozaj chcete zmazať nárok na dovolenku pre{' '}
              <strong>{employeeName(deleting.employee_id)}</strong> za rok{' '}
              <strong>{deleting.year}</strong>?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleting(null)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zrušiť
              </button>
              <button
                onClick={handleDelete}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Zmazať
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default LeaveEntitlementsPage
