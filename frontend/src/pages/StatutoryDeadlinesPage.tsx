import { useCallback, useEffect, useState } from 'react'
import type {
  StatutoryDeadlineRead,
  StatutoryDeadlineCreate,
  StatutoryDeadlineUpdate,
  DeadlineType,
} from '@/types/statutory-deadline'
import {
  listStatutoryDeadlines,
  createStatutoryDeadline,
  updateStatutoryDeadline,
  deleteStatutoryDeadline,
} from '@/services/statutory-deadline.service'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

const DEADLINE_TYPE_OPTIONS: { value: DeadlineType; label: string }[] = [
  { value: 'sp_monthly', label: 'SP mesacne' },
  { value: 'zp_monthly', label: 'ZP mesacne' },
  { value: 'tax_advance', label: 'Preddavok na dan' },
  { value: 'tax_reconciliation', label: 'Rocne zuctovanie dane' },
  { value: 'sp_annual', label: 'SP rocne' },
  { value: 'zp_annual', label: 'ZP rocne' },
]

function deadlineTypeLabel(dt: DeadlineType): string {
  return DEADLINE_TYPE_OPTIONS.find((o) => o.value === dt)?.label ?? dt
}

// -- Empty form state --------------------------------------------------------
interface FormState {
  deadline_type: DeadlineType
  institution: string
  day_of_month: string
  description: string
  valid_from: string
  valid_to: string
  is_active: boolean
}

const EMPTY_FORM: FormState = {
  deadline_type: 'sp_monthly',
  institution: '',
  day_of_month: '',
  description: '',
  valid_from: '',
  valid_to: '',
  is_active: true,
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): StatutoryDeadlineCreate {
  return {
    deadline_type: form.deadline_type,
    institution: form.institution,
    day_of_month: Number(form.day_of_month),
    description: form.description,
    valid_from: form.valid_from,
    valid_to: form.valid_to || null,
    is_active: form.is_active,
  }
}

function toUpdatePayload(form: FormState): StatutoryDeadlineUpdate {
  return {
    deadline_type: form.deadline_type,
    institution: form.institution,
    day_of_month: Number(form.day_of_month),
    description: form.description,
    valid_from: form.valid_from,
    valid_to: form.valid_to || null,
    is_active: form.is_active,
  }
}

function deadlineToForm(d: StatutoryDeadlineRead): FormState {
  return {
    deadline_type: d.deadline_type,
    institution: d.institution,
    day_of_month: String(d.day_of_month),
    description: d.description,
    valid_from: d.valid_from,
    valid_to: d.valid_to ?? '',
    is_active: d.is_active,
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

// -- Component ---------------------------------------------------------------
function StatutoryDeadlinesPage() {
  // List state
  const [items, setItems] = useState<StatutoryDeadlineRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<StatutoryDeadlineRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<StatutoryDeadlineRead | null>(null)

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listStatutoryDeadlines({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nepodarilo sa nacitat data')
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
    setForm(EMPTY_FORM)
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(deadline: StatutoryDeadlineRead) {
    setEditing(deadline)
    setForm(deadlineToForm(deadline))
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
        await updateStatutoryDeadline(editing.id, toUpdatePayload(form))
      } else {
        await createStatutoryDeadline(toCreatePayload(form))
      }
      closeModal()
      await fetchData()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Chyba pri ukladani')
    } finally {
      setSubmitting(false)
    }
  }

  // -- Delete handlers -------------------------------------------------------
  async function handleDelete() {
    if (!deleting) return
    try {
      await deleteStatutoryDeadline(deleting.id)
      setDeleting(null)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri mazani')
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
          <h1 className="text-2xl font-bold text-gray-900">Zakonné terminy</h1>
          <p className="mt-1 text-sm text-gray-600">
            Sprava zakonnych terminov pre SP, ZP a dane
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Novy termin
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
                Typ
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Institucia
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Den v mesiaci
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Popis
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Platnost od
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Platnost do
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
                  Nacitavam...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-500">
                  Ziadne zakonné terminy
                </td>
              </tr>
            )}
            {!loading &&
              items.map((deadline) => (
                <tr key={deadline.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {deadlineTypeLabel(deadline.deadline_type)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {deadline.institution}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-center text-sm text-gray-700">
                    {deadline.day_of_month}.
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-sm text-gray-700">
                    {deadline.description}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(deadline.valid_from)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(deadline.valid_to)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-center text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        deadline.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {deadline.is_active ? 'Aktivny' : 'Neaktivny'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => openEdit(deadline)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upravit
                    </button>
                    <button
                      onClick={() => setDeleting(deadline)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Zmazat
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
              Zobrazenych {page * PAGE_SIZE + 1}&ndash;{Math.min((page + 1) * PAGE_SIZE, total)} z {total}
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

      {/* -- Create/Edit Modal ------------------------------------------------ */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              {editing ? 'Upravit termin' : 'Novy zakonny termin'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Deadline Type + Day of Month */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Typ terminu</label>
                  <select
                    required
                    value={form.deadline_type}
                    onChange={(e) => updateField('deadline_type', e.target.value as DeadlineType)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    {DEADLINE_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Den v mesiaci</label>
                  <input
                    type="number"
                    required
                    min={1}
                    max={31}
                    value={form.day_of_month}
                    onChange={(e) => updateField('day_of_month', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 8"
                  />
                </div>
              </div>

              {/* Institution */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Institucia</label>
                <input
                  type="text"
                  required
                  value={form.institution}
                  onChange={(e) => updateField('institution', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="napr. Socialna poistovna"
                />
              </div>

              {/* Description */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Popis</label>
                <input
                  type="text"
                  required
                  value={form.description}
                  onChange={(e) => updateField('description', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="napr. Mesacny vykaz a odvody SP"
                />
              </div>

              {/* Valid From + Valid To */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Platnost od</label>
                  <input
                    type="date"
                    required
                    value={form.valid_from}
                    onChange={(e) => updateField('valid_from', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Platnost do <span className="text-gray-400">(volitelne)</span>
                  </label>
                  <input
                    type="date"
                    value={form.valid_to}
                    onChange={(e) => updateField('valid_to', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Is Active */}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={form.is_active}
                  onChange={(e) => updateField('is_active', e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                  Aktivny
                </label>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Zrusit
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {submitting ? 'Ukladam...' : editing ? 'Ulozit zmeny' : 'Vytvorit'}
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
            <h2 className="mb-2 text-lg font-semibold text-gray-900">Potvrdit zmazanie</h2>
            <p className="mb-4 text-sm text-gray-600">
              Naozaj chcete zmazat termin <strong>{deadlineTypeLabel(deleting.deadline_type)}</strong> ({deleting.institution})?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleting(null)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zrusit
              </button>
              <button
                onClick={handleDelete}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Zmazat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default StatutoryDeadlinesPage
