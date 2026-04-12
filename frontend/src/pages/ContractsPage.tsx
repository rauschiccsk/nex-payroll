import { useCallback, useEffect, useState } from 'react'
import type { ContractRead, ContractCreate, ContractUpdate, ContractType, WageType } from '@/types/contract'
import type { EmployeeRead } from '@/types/employee'
import {
  listContracts,
  createContract,
  updateContract,
  deleteContract,
} from '@/services/contract.service'
import { listEmployees } from '@/services/employee.service'
import { authStore } from '@/stores/auth.store'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

// -- Label maps --------------------------------------------------------------
const CONTRACT_TYPE_LABELS: Record<ContractType, string> = {
  permanent: 'Trvalý pomer',
  fixed_term: 'Doba určitá',
  agreement_work: 'Dohoda o práci',
  agreement_activity: 'Dohoda o činnosti',
}

const WAGE_TYPE_LABELS: Record<WageType, string> = {
  monthly: 'Mesačná',
  hourly: 'Hodinová',
}

const CONTRACT_TYPE_COLORS: Record<ContractType, string> = {
  permanent: 'bg-blue-100 text-blue-800',
  fixed_term: 'bg-yellow-100 text-yellow-800',
  agreement_work: 'bg-purple-100 text-purple-800',
  agreement_activity: 'bg-indigo-100 text-indigo-800',
}

// -- Empty form state --------------------------------------------------------
interface FormState {
  tenant_id: string
  employee_id: string
  contract_number: string
  contract_type: ContractType
  job_title: string
  wage_type: WageType
  base_wage: string
  hours_per_week: string
  start_date: string
  end_date: string
  probation_end_date: string
  termination_date: string
  termination_reason: string
  is_current: boolean
}

const EMPTY_FORM: FormState = {
  tenant_id: '',
  employee_id: '',
  contract_number: '',
  contract_type: 'permanent',
  job_title: '',
  wage_type: 'monthly',
  base_wage: '',
  hours_per_week: '40.0',
  start_date: '',
  end_date: '',
  probation_end_date: '',
  termination_date: '',
  termination_reason: '',
  is_current: true,
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): ContractCreate {
  return {
    tenant_id: form.tenant_id,
    employee_id: form.employee_id,
    contract_number: form.contract_number,
    contract_type: form.contract_type,
    job_title: form.job_title,
    wage_type: form.wage_type,
    base_wage: form.base_wage,
    hours_per_week: form.hours_per_week || undefined,
    start_date: form.start_date,
    end_date: form.end_date || null,
    probation_end_date: form.probation_end_date || null,
    termination_date: form.termination_date || null,
    termination_reason: form.termination_reason || null,
    is_current: form.is_current,
  }
}

function toUpdatePayload(form: FormState): ContractUpdate {
  return {
    contract_number: form.contract_number,
    contract_type: form.contract_type,
    job_title: form.job_title,
    wage_type: form.wage_type,
    base_wage: form.base_wage,
    hours_per_week: form.hours_per_week || null,
    start_date: form.start_date,
    end_date: form.end_date || null,
    probation_end_date: form.probation_end_date || null,
    termination_date: form.termination_date || null,
    termination_reason: form.termination_reason || null,
    is_current: form.is_current,
  }
}

function contractToForm(c: ContractRead): FormState {
  return {
    tenant_id: c.tenant_id,
    employee_id: c.employee_id,
    contract_number: c.contract_number,
    contract_type: c.contract_type,
    job_title: c.job_title,
    wage_type: c.wage_type,
    base_wage: String(c.base_wage),
    hours_per_week: String(c.hours_per_week),
    start_date: c.start_date,
    end_date: c.end_date ?? '',
    probation_end_date: c.probation_end_date ?? '',
    termination_date: c.termination_date ?? '',
    termination_reason: c.termination_reason ?? '',
    is_current: c.is_current,
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

function formatWage(amount: string, wageType: WageType): string {
  const num = parseFloat(amount)
  const formatted = isNaN(num) ? amount : num.toLocaleString('sk-SK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return `${formatted} \u20AC${wageType === 'hourly' ? '/hod' : '/mes'}`
}

// -- Component ---------------------------------------------------------------
function ContractsPage() {
  // List state
  const [items, setItems] = useState<ContractRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail state
  const [detail, setDetail] = useState<ContractRead | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<ContractRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<ContractRead | null>(null)

  // Employees for dropdown
  const [employees, setEmployees] = useState<EmployeeRead[]>([])

  // -- Fetch -----------------------------------------------------------------
  useEffect(() => {
    listEmployees({ skip: 0, limit: 100 })
      .then((res) => setEmployees(res.items))
      .catch(() => {/* silently ignore – dropdown will be empty */})
  }, [])

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listContracts({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
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

  function openEdit(contract: ContractRead) {
    setEditing(contract)
    setForm(contractToForm(contract))
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
        await updateContract(editing.id, toUpdatePayload(form))
      } else {
        await createContract(toCreatePayload(form))
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
      await deleteContract(deleting.id)
      setDeleting(null)
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

  // -- Render ----------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Zmluvy</h1>
          <p className="mt-1 text-sm text-gray-600">
            Pracovné zmluvy a dohody zamestnancov
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nová zmluva
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
                Číslo zmluvy
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Typ
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Pozicia
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Mzda
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Od
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Do
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
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
                <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-500">
                  Načítavam...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-500">
                  Žiadne zmluvy
                </td>
              </tr>
            )}
            {!loading &&
              items.map((contract) => (
                <tr key={contract.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium font-mono text-gray-900">
                    {contract.contract_number}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        CONTRACT_TYPE_COLORS[contract.contract_type]
                      }`}
                    >
                      {CONTRACT_TYPE_LABELS[contract.contract_type]}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {contract.job_title}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-mono text-gray-700">
                    {formatWage(contract.base_wage, contract.wage_type)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(contract.start_date)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(contract.end_date)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-center text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        contract.is_current
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {contract.is_current ? 'Aktívna' : 'Ukončená'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(contract)}
                      className="mr-2 text-gray-600 hover:text-gray-800"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(contract)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upraviť
                    </button>
                    <button
                      onClick={() => setDeleting(contract)}
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
      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                Zmluva {detail.contract_number}
              </h2>
              <span
                className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                  detail.is_current
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                {detail.is_current ? 'Aktívna' : 'Ukončená'}
              </span>
            </div>

            {/* Contract info */}
            <div className="space-y-4">
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Základné údaje</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Číslo zmluvy</dt>
                    <dd className="font-medium font-mono text-gray-900">{detail.contract_number}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Typ zmluvy</dt>
                    <dd className="font-medium text-gray-900">
                      {CONTRACT_TYPE_LABELS[detail.contract_type]}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Pozícia</dt>
                    <dd className="font-medium text-gray-900">{detail.job_title}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Zamestnanec ID</dt>
                    <dd className="font-medium font-mono text-gray-900 text-xs">{detail.employee_id}</dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Mzda</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Typ mzdy</dt>
                    <dd className="font-medium text-gray-900">{WAGE_TYPE_LABELS[detail.wage_type]}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Základná mzda</dt>
                    <dd className="font-medium font-mono text-gray-900">
                      {formatWage(detail.base_wage, detail.wage_type)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Hodín/týždeň</dt>
                    <dd className="font-medium text-gray-900">{detail.hours_per_week}</dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Dátumy</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Začiatok</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.start_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Koniec</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.end_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Koniec skúšobnej doby</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.probation_end_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Dátum ukončenia</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.termination_date)}</dd>
                  </div>
                  {detail.termination_reason && (
                    <div className="col-span-2">
                      <dt className="text-gray-500">Dôvod ukončenia</dt>
                      <dd className="font-medium text-gray-900">{detail.termination_reason}</dd>
                    </div>
                  )}
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
              {editing ? 'Upraviť zmluvu' : 'Nová zmluva'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Employee — only for create (tenant_id auto-populated from auth) */}
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

              {/* Contract number + type */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Číslo zmluvy
                  </label>
                  <input
                    type="text"
                    required
                    value={form.contract_number}
                    onChange={(e) => updateField('contract_number', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. PZ-2024-001"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Typ zmluvy</label>
                  <select
                    value={form.contract_type}
                    onChange={(e) => updateField('contract_type', e.target.value as ContractType)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    <option value="permanent">{CONTRACT_TYPE_LABELS['permanent']}</option>
                    <option value="fixed_term">{CONTRACT_TYPE_LABELS['fixed_term']}</option>
                    <option value="agreement_work">{CONTRACT_TYPE_LABELS['agreement_work']}</option>
                    <option value="agreement_activity">
                      {CONTRACT_TYPE_LABELS['agreement_activity']}
                    </option>
                  </select>
                </div>
              </div>

              {/* Job title */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Pozícia</label>
                <input
                  type="text"
                  required
                  value={form.job_title}
                  onChange={(e) => updateField('job_title', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="napr. Softvérový vývojár"
                />
              </div>

              {/* Wage type + amount + hours */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Typ mzdy</label>
                  <select
                    value={form.wage_type}
                    onChange={(e) => updateField('wage_type', e.target.value as WageType)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    <option value="monthly">{WAGE_TYPE_LABELS['monthly']}</option>
                    <option value="hourly">{WAGE_TYPE_LABELS['hourly']}</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Základná mzda (&euro;)
                  </label>
                  <input
                    type="number"
                    required
                    step="0.01"
                    min="0"
                    value={form.base_wage}
                    onChange={(e) => updateField('base_wage', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 1500.00"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Hodín/týždeň
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={form.hours_per_week}
                    onChange={(e) => updateField('hours_per_week', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="40.0"
                  />
                </div>
              </div>

              {/* Dates */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Dátum začiatku
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
                    Dátum konca <span className="text-gray-400">(voliteľné)</span>
                  </label>
                  <input
                    type="date"
                    value={form.end_date}
                    onChange={(e) => updateField('end_date', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Koniec skúšobnej doby <span className="text-gray-400">(voliteľné)</span>
                  </label>
                  <input
                    type="date"
                    value={form.probation_end_date}
                    onChange={(e) => updateField('probation_end_date', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Dátum ukončenia <span className="text-gray-400">(voliteľné)</span>
                  </label>
                  <input
                    type="date"
                    value={form.termination_date}
                    onChange={(e) => updateField('termination_date', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Termination reason */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Dôvod ukončenia <span className="text-gray-400">(voliteľné)</span>
                </label>
                <input
                  type="text"
                  value={form.termination_reason}
                  onChange={(e) => updateField('termination_reason', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="napr. Výpoveď dohodou"
                />
              </div>

              {/* Is Current */}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_current"
                  checked={form.is_current}
                  onChange={(e) => updateField('is_current', e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <label htmlFor="is_current" className="text-sm font-medium text-gray-700">
                  Aktívna zmluva
                </label>
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
              Naozaj chcete zmazať zmluvu <strong>{deleting.contract_number}</strong> (
              {CONTRACT_TYPE_LABELS[deleting.contract_type]})?
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

export default ContractsPage
