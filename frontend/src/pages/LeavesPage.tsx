import { useCallback, useEffect, useState } from 'react'
import type { LeaveRead, LeaveCreate, LeaveUpdate, LeaveType, LeaveStatus } from '@/types/leave'
import type { EmployeeRead } from '@/types/employee'
import { listLeaves, createLeave, updateLeave, deleteLeave } from '@/services/leave.service'
import { listEmployees } from '@/services/employee.service'
import { authStore } from '@/stores/auth.store'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

const LEAVE_TYPE_LABELS: Record<LeaveType, string> = {
  annual: 'Dovolenka',
  sick_employer: 'PN (zamestn\u00e1vate\u013e)',
  sick_sp: 'PN (SP)',
  ocr: 'O\u010cR',
  maternity: 'Matersk\u00e1',
  parental: 'Rodi\u010dovsk\u00e1',
  unpaid: 'Neplaten\u00e9 vo\u013eno',
  obstacle: 'Prek\u00e1\u017eky v pr\u00e1ci',
}

const STATUS_LABELS: Record<LeaveStatus, string> = {
  pending: '\u010cakaj\u00faca',
  approved: 'Schv\u00e1len\u00e1',
  rejected: 'Zamietnut\u00e1',
  cancelled: 'Zru\u0161en\u00e1',
}

const STATUS_COLORS: Record<LeaveStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-600',
}

const LEAVE_TYPE_OPTIONS: LeaveType[] = [
  'annual',
  'sick_employer',
  'sick_sp',
  'ocr',
  'maternity',
  'parental',
  'unpaid',
  'obstacle',
]

const STATUS_OPTIONS: LeaveStatus[] = ['pending', 'approved', 'rejected', 'cancelled']

// -- Empty form state --------------------------------------------------------
interface FormState {
  tenant_id: string
  employee_id: string
  leave_type: LeaveType
  start_date: string
  end_date: string
  business_days: string
  status: LeaveStatus
  note: string
}

const EMPTY_FORM: FormState = {
  tenant_id: '',
  employee_id: '',
  leave_type: 'annual',
  start_date: '',
  end_date: '',
  business_days: '0',
  status: 'pending',
  note: '',
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): LeaveCreate {
  return {
    tenant_id: form.tenant_id,
    employee_id: form.employee_id,
    leave_type: form.leave_type,
    start_date: form.start_date,
    end_date: form.end_date,
    business_days: Number(form.business_days),
    status: form.status,
    note: form.note || null,
  }
}

function toUpdatePayload(form: FormState): LeaveUpdate {
  return {
    leave_type: form.leave_type,
    start_date: form.start_date,
    end_date: form.end_date,
    business_days: Number(form.business_days),
    status: form.status,
    note: form.note || null,
  }
}

function leaveToForm(l: LeaveRead): FormState {
  return {
    tenant_id: l.tenant_id,
    employee_id: l.employee_id,
    leave_type: l.leave_type,
    start_date: l.start_date,
    end_date: l.end_date,
    business_days: String(l.business_days),
    status: l.status,
    note: l.note ?? '',
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

// -- Component ---------------------------------------------------------------
function LeavesPage() {
  // List state
  const [items, setItems] = useState<LeaveRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail state
  const [detail, setDetail] = useState<LeaveRead | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<LeaveRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<LeaveRead | null>(null)

  // Employees for dropdown
  const [employees, setEmployees] = useState<EmployeeRead[]>([])

  // Filter state
  const [filterEmployee, setFilterEmployee] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterType, setFilterType] = useState('')

  // -- Fetch -----------------------------------------------------------------
  useEffect(() => {
    listEmployees({ skip: 0, limit: 1000 })
      .then((res) => setEmployees(res.items))
      .catch(() => {
        /* silently ignore - dropdown will be empty */
      })
  }, [])

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, unknown> = {
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }
      if (filterEmployee) params.employee_id = filterEmployee
      if (filterStatus) params.status = filterStatus
      if (filterType) params.leave_type = filterType
      const res = await listLeaves(params)
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nepodarilo sa na\u010d\u00edta\u0165 d\u00e1ta')
    } finally {
      setLoading(false)
    }
  }, [page, filterEmployee, filterStatus, filterType])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // -- Filter handlers -------------------------------------------------------
  function handleFilterChange(
    setter: React.Dispatch<React.SetStateAction<string>>,
    value: string,
  ) {
    setter(value)
    setPage(0)
  }

  function clearFilters() {
    setFilterEmployee('')
    setFilterStatus('')
    setFilterType('')
    setPage(0)
  }

  const hasActiveFilters = filterEmployee || filterStatus || filterType

  // -- Modal handlers --------------------------------------------------------
  function openCreate() {
    setEditing(null)
    const tenantId = authStore.getState().tenantId ?? ''
    setForm({ ...EMPTY_FORM, tenant_id: tenantId })
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(leave: LeaveRead) {
    setEditing(leave)
    setForm(leaveToForm(leave))
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
        await updateLeave(editing.id, toUpdatePayload(form))
      } else {
        await createLeave(toCreatePayload(form))
      }
      closeModal()
      await fetchData()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Chyba pri ukladan\u00ed')
    } finally {
      setSubmitting(false)
    }
  }

  // -- Delete handlers -------------------------------------------------------
  async function handleDelete() {
    if (!deleting) return
    try {
      await deleteLeave(deleting.id)
      setDeleting(null)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri mazan\u00ed')
      setDeleting(null)
    }
  }

  // -- Form field updater ----------------------------------------------------
  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
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
          <h1 className="text-2xl font-bold text-gray-900">Dovolenky a nepr\u00edtomnos\u0165</h1>
          <p className="mt-1 text-sm text-gray-600">
            Evidencia dovoleniek, PN, O\u010cR a \u010fal\u0161\u00edch nepr\u00edtomnost\u00ed
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nov\u00e1 \u017eiados\u0165
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="min-w-[180px]">
          <label className="mb-1 block text-xs font-medium text-gray-500">Zamestnanec</label>
          <select
            value={filterEmployee}
            onChange={(e) => handleFilterChange(setFilterEmployee, e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            data-testid="filter-employee"
          >
            <option value="">V\u0161etci</option>
            {employees.map((emp) => (
              <option key={emp.id} value={emp.id}>
                {emp.last_name} {emp.first_name}
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-[150px]">
          <label className="mb-1 block text-xs font-medium text-gray-500">Typ</label>
          <select
            value={filterType}
            onChange={(e) => handleFilterChange(setFilterType, e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            data-testid="filter-type"
          >
            <option value="">V\u0161etky</option>
            {LEAVE_TYPE_OPTIONS.map((t) => (
              <option key={t} value={t}>
                {LEAVE_TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-[140px]">
          <label className="mb-1 block text-xs font-medium text-gray-500">Stav</label>
          <select
            value={filterStatus}
            onChange={(e) => handleFilterChange(setFilterStatus, e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            data-testid="filter-status"
          >
            <option value="">V\u0161etky</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          >
            Zru\u0161i\u0165 filtre
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
                Zamestnanec
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Typ
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Od
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Do
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Prac. dni
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Stav
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
                  Na\u010d\u00edtavam...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                  \u017diadne z\u00e1znamy
                </td>
              </tr>
            )}
            {!loading &&
              items.map((leave) => (
                <tr key={leave.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {employeeName(leave.employee_id)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {LEAVE_TYPE_LABELS[leave.leave_type]}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(leave.start_date)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(leave.end_date)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                    {leave.business_days}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[leave.status]}`}
                    >
                      {STATUS_LABELS[leave.status]}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(leave)}
                      className="mr-2 text-gray-600 hover:text-gray-800"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(leave)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upravi\u0165
                    </button>
                    <button
                      onClick={() => setDeleting(leave)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Zmaza\u0165
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
              Zobrazen\u00fdch {page * PAGE_SIZE + 1}&ndash;
              {Math.min((page + 1) * PAGE_SIZE, total)} z {total}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Predch\u00e1dzaj\u00faca
              </button>
              <span className="flex items-center px-2 text-sm text-gray-700">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Nasleduj\u00faca
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
                Nepr\u00edtomnos\u0165 &mdash; {employeeName(detail.employee_id)}
              </h2>
            </div>

            <div className="space-y-4">
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Z\u00e1kladn\u00e9 \u00fadaje</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Zamestnanec</dt>
                    <dd className="font-medium text-gray-900">
                      {employeeName(detail.employee_id)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Typ</dt>
                    <dd className="font-medium text-gray-900">
                      {LEAVE_TYPE_LABELS[detail.leave_type]}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Stav</dt>
                    <dd>
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[detail.status]}`}
                      >
                        {STATUS_LABELS[detail.status]}
                      </span>
                    </dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Obdobie</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Od</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.start_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Do</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.end_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Pracovn\u00e9 dni</dt>
                    <dd className="font-medium text-gray-900">{detail.business_days}</dd>
                  </div>
                </dl>
              </fieldset>

              {detail.note && (
                <fieldset className="rounded-lg border border-gray-200 p-4">
                  <legend className="px-2 text-sm font-medium text-gray-500">Pozn\u00e1mka</legend>
                  <p className="text-sm text-gray-700">{detail.note}</p>
                </fieldset>
              )}

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Schv\u00e1lenie</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Schv\u00e1len\u00e9 d\u0148a</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.approved_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Schv\u00e1lil</dt>
                    <dd className="font-medium text-gray-900">
                      {detail.approved_by ? detail.approved_by.slice(0, 8) + '...' : '\u2014'}
                    </dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Syst\u00e9m</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Vytvoren\u00e9</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.created_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Aktualizovan\u00e9</dt>
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
                Upravi\u0165
              </button>
              <button
                onClick={() => setDetail(null)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zavrie\u0165
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
              {editing ? 'Upravi\u0165 nepr\u00edtomnos\u0165' : 'Nov\u00e1 \u017eiados\u0165 o nepr\u00edtomnos\u0165'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Employee - only for create */}
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
                    <option value="">-- Vyberte zamestnanca --</option>
                    {employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.last_name} {emp.first_name} ({emp.employee_number})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Leave type */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Typ nepr\u00edtomnosti
                </label>
                <select
                  required
                  value={form.leave_type}
                  onChange={(e) => updateField('leave_type', e.target.value as LeaveType)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  {LEAVE_TYPE_OPTIONS.map((type) => (
                    <option key={type} value={type}>
                      {LEAVE_TYPE_LABELS[type]}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date range */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    D\u00e1tum od
                  </label>
                  <input
                    type="date"
                    required
                    value={form.start_date}
                    onChange={(e) => updateField('start_date', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    D\u00e1tum do
                  </label>
                  <input
                    type="date"
                    required
                    value={form.end_date}
                    onChange={(e) => updateField('end_date', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Business days + Status */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Pracovn\u00e9 dni
                  </label>
                  <input
                    type="number"
                    required
                    min={0}
                    max={365}
                    value={form.business_days}
                    onChange={(e) => updateField('business_days', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Stav</label>
                  <select
                    required
                    value={form.status}
                    onChange={(e) => updateField('status', e.target.value as LeaveStatus)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    {STATUS_OPTIONS.map((st) => (
                      <option key={st} value={st}>
                        {STATUS_LABELS[st]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Note */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Pozn\u00e1mka
                </label>
                <textarea
                  value={form.note}
                  onChange={(e) => updateField('note', e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="Volite\u013en\u00e1 pozn\u00e1mka..."
                />
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Zru\u0161i\u0165
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {submitting
                    ? 'Uklad\u00e1m...'
                    : editing
                      ? 'Ulo\u017ei\u0165 zmeny'
                      : 'Vytvori\u0165'}
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
            <h2 className="mb-2 text-lg font-semibold text-gray-900">Potvrdi\u0165 zmazanie</h2>
            <p className="mb-4 text-sm text-gray-600">
              Naozaj chcete zmaza\u0165 {LEAVE_TYPE_LABELS[deleting.leave_type].toLowerCase()} pre{' '}
              <strong>{employeeName(deleting.employee_id)}</strong> ({formatDate(deleting.start_date)}{' '}
              &ndash; {formatDate(deleting.end_date)})?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleting(null)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zru\u0161i\u0165
              </button>
              <button
                onClick={handleDelete}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Zmaza\u0165
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default LeavesPage
