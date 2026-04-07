import { useCallback, useEffect, useState } from 'react'
import type { EmployeeChildRead, EmployeeChildCreate, EmployeeChildUpdate } from '@/types/employee-child'
import type { EmployeeRead } from '@/types/employee'
import {
  listEmployeeChildren,
  createEmployeeChild,
  updateEmployeeChild,
  deleteEmployeeChild,
} from '@/services/employee-child.service'
import { listEmployees } from '@/services/employee.service'
import { authStore } from '@/stores/auth.store'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

// -- Empty form state --------------------------------------------------------
interface FormState {
  tenant_id: string
  employee_id: string
  first_name: string
  last_name: string
  birth_date: string
  birth_number: string
  is_tax_bonus_eligible: boolean
  custody_from: string
  custody_to: string
}

const EMPTY_FORM: FormState = {
  tenant_id: '',
  employee_id: '',
  first_name: '',
  last_name: '',
  birth_date: '',
  birth_number: '',
  is_tax_bonus_eligible: true,
  custody_from: '',
  custody_to: '',
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): EmployeeChildCreate {
  return {
    tenant_id: form.tenant_id,
    employee_id: form.employee_id,
    first_name: form.first_name,
    last_name: form.last_name,
    birth_date: form.birth_date,
    birth_number: form.birth_number || null,
    is_tax_bonus_eligible: form.is_tax_bonus_eligible,
    custody_from: form.custody_from || null,
    custody_to: form.custody_to || null,
  }
}

function toUpdatePayload(form: FormState): EmployeeChildUpdate {
  return {
    first_name: form.first_name,
    last_name: form.last_name,
    birth_date: form.birth_date,
    birth_number: form.birth_number || null,
    is_tax_bonus_eligible: form.is_tax_bonus_eligible,
    custody_from: form.custody_from || null,
    custody_to: form.custody_to || null,
  }
}

function childToForm(c: EmployeeChildRead): FormState {
  return {
    tenant_id: c.tenant_id,
    employee_id: c.employee_id,
    first_name: c.first_name,
    last_name: c.last_name,
    birth_date: c.birth_date,
    birth_number: c.birth_number ?? '',
    is_tax_bonus_eligible: c.is_tax_bonus_eligible,
    custody_from: c.custody_from ?? '',
    custody_to: c.custody_to ?? '',
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

// -- Component ---------------------------------------------------------------
function EmployeeChildrenPage() {
  // List state
  const [items, setItems] = useState<EmployeeChildRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail state
  const [detail, setDetail] = useState<EmployeeChildRead | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<EmployeeChildRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<EmployeeChildRead | null>(null)

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
      const res = await listEmployeeChildren({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
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

  function openEdit(child: EmployeeChildRead) {
    setEditing(child)
    setForm(childToForm(child))
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
        await updateEmployeeChild(editing.id, toUpdatePayload(form))
      } else {
        await createEmployeeChild(toCreatePayload(form))
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
      await deleteEmployeeChild(deleting.id)
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
          <h1 className="text-2xl font-bold text-gray-900">Deti zamestnancov</h1>
          <p className="mt-1 text-sm text-gray-600">
            Evidencia detí pre daňový bonus a sociálne dávky
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nové dieťa
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
                Meno a priezvisko
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Zamestnanec
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Dátum narodenia
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Daňový bonus
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Starostlivosť od
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Starostlivosť do
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
              items.map((child) => (
                <tr key={child.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {child.last_name} {child.first_name}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {employeeName(child.employee_id)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(child.birth_date)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-center text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        child.is_tax_bonus_eligible
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {child.is_tax_bonus_eligible ? 'Áno' : 'Nie'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(child.custody_from)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(child.custody_to)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(child)}
                      className="mr-2 text-gray-600 hover:text-gray-800"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(child)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upraviť
                    </button>
                    <button
                      onClick={() => setDeleting(child)}
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
                Dieťa — {detail.last_name} {detail.first_name}
              </h2>
              <span
                className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                  detail.is_tax_bonus_eligible
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                {detail.is_tax_bonus_eligible ? 'Daňový bonus' : 'Bez bonusu'}
              </span>
            </div>

            <div className="space-y-4">
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Osobné údaje</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Meno</dt>
                    <dd className="font-medium text-gray-900">{detail.first_name}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Priezvisko</dt>
                    <dd className="font-medium text-gray-900">{detail.last_name}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Dátum narodenia</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.birth_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Rodné číslo</dt>
                    <dd className="font-medium font-mono text-gray-900">
                      {detail.birth_number ?? '\u2014'}
                    </dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Zamestnanec</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Zamestnanec</dt>
                    <dd className="font-medium text-gray-900">{employeeName(detail.employee_id)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Osobné číslo</dt>
                    <dd className="font-medium font-mono text-gray-900 text-xs">
                      {employees.find((e) => e.id === detail.employee_id)?.employee_number ?? '—'}
                    </dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Starostlivosť & bonus</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Daňový bonus</dt>
                    <dd className="font-medium text-gray-900">
                      {detail.is_tax_bonus_eligible ? 'Áno' : 'Nie'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Starostlivosť od</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.custody_from)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Starostlivosť do</dt>
                    <dd className="font-medium text-gray-900">{formatDate(detail.custody_to)}</dd>
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
              {editing ? 'Upraviť dieťa' : 'Nové dieťa'}
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

              {/* Name fields */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Meno</label>
                  <input
                    type="text"
                    required
                    value={form.first_name}
                    onChange={(e) => updateField('first_name', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. Ján"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Priezvisko</label>
                  <input
                    type="text"
                    required
                    value={form.last_name}
                    onChange={(e) => updateField('last_name', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. Novák"
                  />
                </div>
              </div>

              {/* Birth date + birth number */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Dátum narodenia
                  </label>
                  <input
                    type="date"
                    required
                    value={form.birth_date}
                    onChange={(e) => updateField('birth_date', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Rodné číslo <span className="text-gray-400">(voliteľné)</span>
                  </label>
                  <input
                    type="text"
                    value={form.birth_number}
                    onChange={(e) => updateField('birth_number', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 150320/1234"
                    maxLength={20}
                  />
                </div>
              </div>

              {/* Custody dates */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Starostlivosť od <span className="text-gray-400">(voliteľné)</span>
                  </label>
                  <input
                    type="date"
                    value={form.custody_from}
                    onChange={(e) => updateField('custody_from', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Starostlivosť do <span className="text-gray-400">(voliteľné)</span>
                  </label>
                  <input
                    type="date"
                    value={form.custody_to}
                    onChange={(e) => updateField('custody_to', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Tax bonus checkbox */}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_tax_bonus_eligible"
                  checked={form.is_tax_bonus_eligible}
                  onChange={(e) => updateField('is_tax_bonus_eligible', e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <label htmlFor="is_tax_bonus_eligible" className="text-sm font-medium text-gray-700">
                  Nárok na daňový bonus
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
              Naozaj chcete zmazať záznam dieťaťa{' '}
              <strong>
                {deleting.last_name} {deleting.first_name}
              </strong>
              ?
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

export default EmployeeChildrenPage
