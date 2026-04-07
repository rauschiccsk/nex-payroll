import { useCallback, useEffect, useState } from 'react'
import type {
  EmployeeRead,
  EmployeeCreate,
  EmployeeUpdate,
  Gender,
  TaxDeclarationType,
  EmployeeStatus,
} from '@/types/employee'
import type { HealthInsurerRead } from '@/types/health-insurer'
import {
  listEmployees,
  createEmployee,
  updateEmployee,
  deleteEmployee,
} from '@/services/employee.service'
import { listHealthInsurers } from '@/services/health-insurer.service'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

// -- Form state --------------------------------------------------------------
interface FormState {
  tenant_id: string
  employee_number: string
  first_name: string
  last_name: string
  title_before: string
  title_after: string
  birth_date: string
  birth_number: string
  gender: Gender
  nationality: string
  address_street: string
  address_city: string
  address_zip: string
  address_country: string
  bank_iban: string
  bank_bic: string
  health_insurer_id: string
  tax_declaration_type: TaxDeclarationType
  nczd_applied: boolean
  pillar2_saver: boolean
  is_disabled: boolean
  status: EmployeeStatus
  hire_date: string
  termination_date: string
}

const EMPTY_FORM: FormState = {
  tenant_id: '',
  employee_number: '',
  first_name: '',
  last_name: '',
  title_before: '',
  title_after: '',
  birth_date: '',
  birth_number: '',
  gender: 'M',
  nationality: 'SK',
  address_street: '',
  address_city: '',
  address_zip: '',
  address_country: 'SK',
  bank_iban: '',
  bank_bic: '',
  health_insurer_id: '',
  tax_declaration_type: 'standard',
  nczd_applied: true,
  pillar2_saver: false,
  is_disabled: false,
  status: 'active',
  hire_date: '',
  termination_date: '',
}

// -- Labels ------------------------------------------------------------------
const GENDER_LABELS: Record<Gender, string> = {
  M: 'Muž',
  F: 'Žena',
}

const TAX_LABELS: Record<TaxDeclarationType, string> = {
  standard: 'Štandardné',
  secondary: 'Vedľajšie',
  none: 'Žiadne',
}

const STATUS_LABELS: Record<EmployeeStatus, string> = {
  active: 'Aktívny',
  inactive: 'Neaktívny',
  terminated: 'Ukončený',
}

const STATUS_COLORS: Record<EmployeeStatus, string> = {
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-yellow-100 text-yellow-800',
  terminated: 'bg-red-100 text-red-800',
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): EmployeeCreate {
  return {
    tenant_id: form.tenant_id,
    employee_number: form.employee_number,
    first_name: form.first_name,
    last_name: form.last_name,
    title_before: form.title_before || null,
    title_after: form.title_after || null,
    birth_date: form.birth_date,
    birth_number: form.birth_number,
    gender: form.gender,
    nationality: form.nationality || 'SK',
    address_street: form.address_street,
    address_city: form.address_city,
    address_zip: form.address_zip,
    address_country: form.address_country || 'SK',
    bank_iban: form.bank_iban,
    bank_bic: form.bank_bic || null,
    health_insurer_id: form.health_insurer_id,
    tax_declaration_type: form.tax_declaration_type,
    nczd_applied: form.nczd_applied,
    pillar2_saver: form.pillar2_saver,
    is_disabled: form.is_disabled,
    status: form.status,
    hire_date: form.hire_date,
    termination_date: form.termination_date || null,
  }
}

function toUpdatePayload(form: FormState): EmployeeUpdate {
  return {
    employee_number: form.employee_number,
    first_name: form.first_name,
    last_name: form.last_name,
    title_before: form.title_before || null,
    title_after: form.title_after || null,
    birth_date: form.birth_date,
    birth_number: form.birth_number,
    gender: form.gender,
    nationality: form.nationality || 'SK',
    address_street: form.address_street,
    address_city: form.address_city,
    address_zip: form.address_zip,
    address_country: form.address_country || 'SK',
    bank_iban: form.bank_iban,
    bank_bic: form.bank_bic || null,
    health_insurer_id: form.health_insurer_id,
    tax_declaration_type: form.tax_declaration_type,
    nczd_applied: form.nczd_applied,
    pillar2_saver: form.pillar2_saver,
    is_disabled: form.is_disabled,
    status: form.status,
    hire_date: form.hire_date,
    termination_date: form.termination_date || null,
  }
}

function employeeToForm(emp: EmployeeRead): FormState {
  return {
    tenant_id: emp.tenant_id,
    employee_number: emp.employee_number,
    first_name: emp.first_name,
    last_name: emp.last_name,
    title_before: emp.title_before ?? '',
    title_after: emp.title_after ?? '',
    birth_date: emp.birth_date,
    birth_number: emp.birth_number,
    gender: emp.gender,
    nationality: emp.nationality,
    address_street: emp.address_street,
    address_city: emp.address_city,
    address_zip: emp.address_zip,
    address_country: emp.address_country,
    bank_iban: emp.bank_iban,
    bank_bic: emp.bank_bic ?? '',
    health_insurer_id: emp.health_insurer_id,
    tax_declaration_type: emp.tax_declaration_type,
    nczd_applied: emp.nczd_applied,
    pillar2_saver: emp.pillar2_saver,
    is_disabled: emp.is_disabled,
    status: emp.status,
    hire_date: emp.hire_date,
    termination_date: emp.termination_date ?? '',
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

function fullName(emp: EmployeeRead): string {
  const parts: string[] = []
  if (emp.title_before) parts.push(emp.title_before)
  parts.push(emp.first_name, emp.last_name)
  if (emp.title_after) parts.push(emp.title_after)
  return parts.join(' ')
}

// -- Component ---------------------------------------------------------------
function EmployeesPage() {
  // List state
  const [items, setItems] = useState<EmployeeRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<EmployeeRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Detail view
  const [detail, setDetail] = useState<EmployeeRead | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<EmployeeRead | null>(null)

  // Health insurers lookup
  const [insurers, setInsurers] = useState<HealthInsurerRead[]>([])

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listEmployees({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nepodarilo sa načítať dáta')
    } finally {
      setLoading(false)
    }
  }, [page])

  const fetchInsurers = useCallback(async () => {
    try {
      const res = await listHealthInsurers({ skip: 0, limit: 100 })
      setInsurers(res.items)
    } catch {
      // silently fail — dropdown will be empty
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    fetchInsurers()
  }, [fetchInsurers])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  function insurerName(id: string): string {
    const ins = insurers.find((i) => i.id === id)
    return ins ? `${ins.code} - ${ins.name}` : id.slice(0, 8)
  }

  // -- Modal handlers --------------------------------------------------------
  function openCreate() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(emp: EmployeeRead) {
    setEditing(emp)
    setForm(employeeToForm(emp))
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
        await updateEmployee(editing.id, toUpdatePayload(form))
      } else {
        await createEmployee(toCreatePayload(form))
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
      await deleteEmployee(deleting.id)
      setDeleting(null)
      if (detail?.id === deleting.id) setDetail(null)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri mazaní')
      setDeleting(null)
    }
  }

  // -- Form field updater ----------------------------------------------------
  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // -- Input class -----------------------------------------------------------
  const inputCls =
    'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500'
  const labelCls = 'mb-1 block text-sm font-medium text-gray-700'

  // -- Render ----------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Zamestnanci</h1>
          <p className="mt-1 text-sm text-gray-600">
            Správa zamestnancov a ich osobných údajov
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nový zamestnanec
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
                Číslo
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Meno a priezvisko
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Dátum narodenia
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Nástup
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Stav
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Poisťovňa
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
                  Žiadni zamestnanci
                </td>
              </tr>
            )}
            {!loading &&
              items.map((emp) => (
                <tr key={emp.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-mono text-gray-700">
                    {emp.employee_number}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    <button
                      onClick={() => setDetail(emp)}
                      className="text-left text-primary-600 hover:text-primary-800 hover:underline"
                    >
                      {fullName(emp)}
                    </button>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(emp.birth_date)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(emp.hire_date)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-center text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[emp.status]}`}
                    >
                      {STATUS_LABELS[emp.status]}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {insurerName(emp.health_insurer_id)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(emp)}
                      className="mr-2 text-gray-600 hover:text-gray-800"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(emp)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upraviť
                    </button>
                    <button
                      onClick={() => setDeleting(emp)}
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
              Zobrazených {page * PAGE_SIZE + 1}&ndash;{Math.min((page + 1) * PAGE_SIZE, total)} z{' '}
              {total}
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
      {detail && !modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                {fullName(detail)}
              </h2>
              <span
                className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[detail.status]}`}
              >
                {STATUS_LABELS[detail.status]}
              </span>
            </div>

            <div className="space-y-4">
              {/* Personal */}
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-500 uppercase">Osobné údaje</h3>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                  <div>
                    <span className="text-gray-500">Číslo zamestnanca:</span>{' '}
                    <span className="font-mono">{detail.employee_number}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Pohlavie:</span>{' '}
                    {GENDER_LABELS[detail.gender]}
                  </div>
                  <div>
                    <span className="text-gray-500">Dátum narodenia:</span>{' '}
                    {formatDate(detail.birth_date)}
                  </div>
                  <div>
                    <span className="text-gray-500">Národnosť:</span> {detail.nationality}
                  </div>
                  <div>
                    <span className="text-gray-500">Rodné číslo:</span>{' '}
                    <span className="font-mono">{detail.birth_number}</span>
                  </div>
                </div>
              </div>

              {/* Address */}
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-500 uppercase">Adresa</h3>
                <p className="text-sm">
                  {detail.address_street}, {detail.address_zip} {detail.address_city},{' '}
                  {detail.address_country}
                </p>
              </div>

              {/* Bank */}
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-500 uppercase">Bankové údaje</h3>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                  <div>
                    <span className="text-gray-500">IBAN:</span>{' '}
                    <span className="font-mono">{detail.bank_iban}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">BIC:</span>{' '}
                    <span className="font-mono">{detail.bank_bic ?? '\u2014'}</span>
                  </div>
                </div>
              </div>

              {/* Employment */}
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-500 uppercase">Pracovné údaje</h3>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                  <div>
                    <span className="text-gray-500">Dátum nástupu:</span>{' '}
                    {formatDate(detail.hire_date)}
                  </div>
                  <div>
                    <span className="text-gray-500">Dátum ukončenia:</span>{' '}
                    {formatDate(detail.termination_date)}
                  </div>
                  <div>
                    <span className="text-gray-500">Poisťovňa:</span>{' '}
                    {insurerName(detail.health_insurer_id)}
                  </div>
                  <div>
                    <span className="text-gray-500">Daňové vyhlásenie:</span>{' '}
                    {TAX_LABELS[detail.tax_declaration_type]}
                  </div>
                </div>
              </div>

              {/* Flags */}
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-500 uppercase">Príznaky</h3>
                <div className="flex flex-wrap gap-2 text-sm">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${detail.nczd_applied ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}
                  >
                    NCZD: {detail.nczd_applied ? 'Ano' : 'Nie'}
                  </span>
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${detail.pillar2_saver ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'}`}
                  >
                    II. pilier: {detail.pillar2_saver ? 'Ano' : 'Nie'}
                  </span>
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${detail.is_disabled ? 'bg-orange-100 text-orange-800' : 'bg-gray-100 text-gray-600'}`}
                  >
                    ZTP: {detail.is_disabled ? 'Ano' : 'Nie'}
                  </span>
                </div>
              </div>

              {/* Timestamps */}
              <div className="border-t border-gray-200 pt-3 text-xs text-gray-400">
                Vytvorené: {formatDate(detail.created_at)} | Aktualizované:{' '}
                {formatDate(detail.updated_at)}
              </div>
            </div>

            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => {
                  setDetail(null)
                  openEdit(detail)
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
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              {editing ? 'Upraviť zamestnanca' : 'Nový zamestnanec'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Section: Personal */}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold text-gray-500 uppercase">
                  Osobné údaje
                </legend>

                <div className="grid grid-cols-3 gap-4">
                  {/* Tenant ID */}
                  {!editing && (
                    <div className="col-span-3">
                      <label className={labelCls}>
                        Tenant ID
                      </label>
                      <input
                        type="text"
                        required
                        value={form.tenant_id}
                        onChange={(e) => updateField('tenant_id', e.target.value)}
                        className={`${inputCls} font-mono`}
                        placeholder="UUID organizácie"
                      />
                    </div>
                  )}

                  <div>
                    <label className={labelCls}>Číslo zamestnanca</label>
                    <input
                      type="text"
                      required
                      value={form.employee_number}
                      onChange={(e) => updateField('employee_number', e.target.value)}
                      className={`${inputCls} font-mono`}
                      placeholder="napr. EMP001"
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Meno</label>
                    <input
                      type="text"
                      required
                      value={form.first_name}
                      onChange={(e) => updateField('first_name', e.target.value)}
                      className={inputCls}
                      placeholder="napr. Jan"
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Priezvisko</label>
                    <input
                      type="text"
                      required
                      value={form.last_name}
                      onChange={(e) => updateField('last_name', e.target.value)}
                      className={inputCls}
                      placeholder="napr. Novak"
                    />
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-4 gap-4">
                  <div>
                    <label className={labelCls}>
                      Titul pred <span className="text-gray-400">(vol.)</span>
                    </label>
                    <input
                      type="text"
                      value={form.title_before}
                      onChange={(e) => updateField('title_before', e.target.value)}
                      className={inputCls}
                      placeholder="napr. Ing."
                    />
                  </div>
                  <div>
                    <label className={labelCls}>
                      Titul za <span className="text-gray-400">(vol.)</span>
                    </label>
                    <input
                      type="text"
                      value={form.title_after}
                      onChange={(e) => updateField('title_after', e.target.value)}
                      className={inputCls}
                      placeholder="napr. PhD."
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Pohlavie</label>
                    <select
                      value={form.gender}
                      onChange={(e) => updateField('gender', e.target.value as Gender)}
                      className={inputCls}
                    >
                      <option value="M">{GENDER_LABELS['M']}</option>
                      <option value="F">{GENDER_LABELS['F']}</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Národnosť</label>
                    <input
                      type="text"
                      value={form.nationality}
                      onChange={(e) => updateField('nationality', e.target.value)}
                      className={inputCls}
                      placeholder="SK"
                    />
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelCls}>Dátum narodenia</label>
                    <input
                      type="date"
                      required
                      value={form.birth_date}
                      onChange={(e) => updateField('birth_date', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Rodné číslo</label>
                    <input
                      type="text"
                      required
                      value={form.birth_number}
                      onChange={(e) => updateField('birth_number', e.target.value)}
                      className={`${inputCls} font-mono`}
                      placeholder="napr. 900101/1234"
                    />
                  </div>
                </div>
              </fieldset>

              {/* Section: Address */}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold text-gray-500 uppercase">
                  Adresa
                </legend>
                <div>
                  <label className={labelCls}>Ulica</label>
                  <input
                    type="text"
                    required
                    value={form.address_street}
                    onChange={(e) => updateField('address_street', e.target.value)}
                    className={inputCls}
                    placeholder="napr. Hlavna 1"
                  />
                </div>
                <div className="mt-4 grid grid-cols-3 gap-4">
                  <div>
                    <label className={labelCls}>Mesto</label>
                    <input
                      type="text"
                      required
                      value={form.address_city}
                      onChange={(e) => updateField('address_city', e.target.value)}
                      className={inputCls}
                      placeholder="napr. Bratislava"
                    />
                  </div>
                  <div>
                    <label className={labelCls}>PSČ</label>
                    <input
                      type="text"
                      required
                      value={form.address_zip}
                      onChange={(e) => updateField('address_zip', e.target.value)}
                      className={inputCls}
                      placeholder="napr. 81101"
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Krajina</label>
                    <input
                      type="text"
                      value={form.address_country}
                      onChange={(e) => updateField('address_country', e.target.value)}
                      className={inputCls}
                      placeholder="SK"
                    />
                  </div>
                </div>
              </fieldset>

              {/* Section: Bank */}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold text-gray-500 uppercase">
                  Bankové údaje
                </legend>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelCls}>IBAN</label>
                    <input
                      type="text"
                      required
                      value={form.bank_iban}
                      onChange={(e) => updateField('bank_iban', e.target.value)}
                      className={`${inputCls} font-mono`}
                      placeholder="SK..."
                    />
                  </div>
                  <div>
                    <label className={labelCls}>
                      BIC <span className="text-gray-400">(voliteľné)</span>
                    </label>
                    <input
                      type="text"
                      value={form.bank_bic}
                      onChange={(e) => updateField('bank_bic', e.target.value)}
                      className={`${inputCls} font-mono`}
                      placeholder="napr. SUBASKBX"
                    />
                  </div>
                </div>
              </fieldset>

              {/* Section: Employment */}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold text-gray-500 uppercase">
                  Pracovné údaje
                </legend>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelCls}>Dátum nástupu</label>
                    <input
                      type="date"
                      required
                      value={form.hire_date}
                      onChange={(e) => updateField('hire_date', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>
                      Dátum ukončenia <span className="text-gray-400">(voliteľné)</span>
                    </label>
                    <input
                      type="date"
                      value={form.termination_date}
                      onChange={(e) => updateField('termination_date', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-3 gap-4">
                  <div>
                    <label className={labelCls}>Stav</label>
                    <select
                      value={form.status}
                      onChange={(e) => updateField('status', e.target.value as EmployeeStatus)}
                      className={inputCls}
                    >
                      <option value="active">{STATUS_LABELS['active']}</option>
                      <option value="inactive">{STATUS_LABELS['inactive']}</option>
                      <option value="terminated">{STATUS_LABELS['terminated']}</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Poisťovňa</label>
                    <select
                      required
                      value={form.health_insurer_id}
                      onChange={(e) => updateField('health_insurer_id', e.target.value)}
                      className={inputCls}
                    >
                      <option value="">-- Vyberte --</option>
                      {insurers.map((ins) => (
                        <option key={ins.id} value={ins.id}>
                          {ins.code} - {ins.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Daňové vyhlásenie</label>
                    <select
                      value={form.tax_declaration_type}
                      onChange={(e) =>
                        updateField('tax_declaration_type', e.target.value as TaxDeclarationType)
                      }
                      className={inputCls}
                    >
                      <option value="standard">{TAX_LABELS['standard']}</option>
                      <option value="secondary">{TAX_LABELS['secondary']}</option>
                      <option value="none">{TAX_LABELS['none']}</option>
                    </select>
                  </div>
                </div>
              </fieldset>

              {/* Section: Flags */}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold text-gray-500 uppercase">
                  Príznaky
                </legend>
                <div className="flex flex-wrap gap-6">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="nczd_applied"
                      checked={form.nczd_applied}
                      onChange={(e) => updateField('nczd_applied', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <label htmlFor="nczd_applied" className="text-sm font-medium text-gray-700">
                      NCZD (nezdaniteľná časť)
                    </label>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="pillar2_saver"
                      checked={form.pillar2_saver}
                      onChange={(e) => updateField('pillar2_saver', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <label htmlFor="pillar2_saver" className="text-sm font-medium text-gray-700">
                      Sporiteľ II. piliera
                    </label>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="is_disabled"
                      checked={form.is_disabled}
                      onChange={(e) => updateField('is_disabled', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <label htmlFor="is_disabled" className="text-sm font-medium text-gray-700">
                      ZTP (zdravotné postihnutie)
                    </label>
                  </div>
                </div>
              </fieldset>

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
                  {submitting ? 'Ukladám...' : editing ? 'Uložiť zmeny' : 'Vytvoriť'}
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
              Naozaj chcete zmazať zamestnanca{' '}
              <strong>
                {deleting.first_name} {deleting.last_name}
              </strong>{' '}
              ({deleting.employee_number})?
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

export default EmployeesPage
