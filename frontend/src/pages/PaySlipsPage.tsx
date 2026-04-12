import { useCallback, useEffect, useState } from 'react'
import type { PaySlipRead, PaySlipCreate, PaySlipUpdate } from '@/types/pay-slip'
import {
  listPaySlips,
  createPaySlip,
  updatePaySlip,
  deletePaySlip,
} from '@/services/pay-slip.service'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

// -- Empty form state --------------------------------------------------------
interface FormState {
  payroll_id: string
  employee_id: string
  period_year: string
  period_month: string
  pdf_path: string
  file_size_bytes: string
  downloaded_at: string
}

const EMPTY_FORM: FormState = {
  payroll_id: '',
  employee_id: '',
  period_year: String(new Date().getFullYear()),
  period_month: String(new Date().getMonth() + 1),
  pdf_path: '',
  file_size_bytes: '',
  downloaded_at: '',
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): PaySlipCreate {
  return {
    payroll_id: form.payroll_id,
    employee_id: form.employee_id,
    period_year: Number(form.period_year),
    period_month: Number(form.period_month),
    pdf_path: form.pdf_path,
    file_size_bytes: form.file_size_bytes ? Number(form.file_size_bytes) : null,
  }
}

function toUpdatePayload(form: FormState, original: PaySlipRead): PaySlipUpdate {
  const payload: PaySlipUpdate = {}
  if (form.pdf_path !== original.pdf_path) payload.pdf_path = form.pdf_path || null
  const origSize = original.file_size_bytes != null ? String(original.file_size_bytes) : ''
  if (form.file_size_bytes !== origSize)
    payload.file_size_bytes = form.file_size_bytes ? Number(form.file_size_bytes) : null
  const origDownloaded = original.downloaded_at ?? ''
  if (form.downloaded_at !== origDownloaded)
    payload.downloaded_at = form.downloaded_at || null
  return payload
}

function slipToForm(s: PaySlipRead): FormState {
  return {
    payroll_id: s.payroll_id,
    employee_id: s.employee_id,
    period_year: String(s.period_year),
    period_month: String(s.period_month),
    pdf_path: s.pdf_path,
    file_size_bytes: s.file_size_bytes != null ? String(s.file_size_bytes) : '',
    downloaded_at: s.downloaded_at ?? '',
  }
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleString('sk-SK')
}

function formatPeriod(year: number, month: number): string {
  return `${String(month).padStart(2, '0')}/${year}`
}

function formatFileSize(bytes: number | null): string {
  if (bytes == null) return '\u2014'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

// -- Component ---------------------------------------------------------------
function PaySlipsPage() {
  // List state
  const [items, setItems] = useState<PaySlipRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail state
  const [detail, setDetail] = useState<PaySlipRead | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<PaySlipRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<PaySlipRead | null>(null)

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listPaySlips({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
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
    setForm({ ...EMPTY_FORM })
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(slip: PaySlipRead) {
    setEditing(slip)
    setForm(slipToForm(slip))
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
        await updatePaySlip(editing.id, toUpdatePayload(form, editing))
      } else {
        await createPaySlip(toCreatePayload(form))
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
      await deletePaySlip(deleting.id)
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
          <h1 className="text-2xl font-bold text-gray-900">Výplatné pásky</h1>
          <p className="mt-1 text-sm text-gray-600">
            Správa vygenerovaných výplatných pások (PDF)
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nová výplatná páska
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
                Obdobie
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Zamestnanec ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                PDF súbor
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Veľkosť
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Vygenerované
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Stiahnuté
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
              items.map((slip) => (
                <tr key={slip.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {formatPeriod(slip.period_year, slip.period_month)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-mono text-gray-700">
                    {slip.employee_id.slice(0, 8)}...
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-sm text-gray-700" title={slip.pdf_path}>
                    {slip.pdf_path.split('/').pop() ?? slip.pdf_path}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                    {formatFileSize(slip.file_size_bytes)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDateTime(slip.generated_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {slip.downloaded_at ? (
                      <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                        {formatDateTime(slip.downloaded_at)}
                      </span>
                    ) : (
                      <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                        Nestiahnuté
                      </span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(slip)}
                      className="mr-2 text-gray-600 hover:text-gray-800"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(slip)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upraviť
                    </button>
                    <button
                      onClick={() => setDeleting(slip)}
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
                Výplatná páska — {formatPeriod(detail.period_year, detail.period_month)}
              </h2>
            </div>

            <div className="space-y-4">
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Obdobie</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Obdobie</dt>
                    <dd className="font-medium text-gray-900">
                      {formatPeriod(detail.period_year, detail.period_month)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Vygenerované</dt>
                    <dd className="font-medium text-gray-900">
                      {formatDateTime(detail.generated_at)}
                    </dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">PDF súbor</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div className="col-span-2">
                    <dt className="text-gray-500">Cesta k súboru</dt>
                    <dd className="break-all font-mono font-medium text-gray-900">
                      {detail.pdf_path}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Veľkosť</dt>
                    <dd className="font-medium text-gray-900">
                      {formatFileSize(detail.file_size_bytes)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Stiahnuté</dt>
                    <dd className="font-medium text-gray-900">
                      {detail.downloaded_at ? (
                        <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                          {formatDateTime(detail.downloaded_at)}
                        </span>
                      ) : (
                        <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                          Nestiahnuté
                        </span>
                      )}
                    </dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Väzby</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Zamestnanec ID</dt>
                    <dd className="font-mono font-medium text-gray-900">{detail.employee_id}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Payroll ID</dt>
                    <dd className="font-mono font-medium text-gray-900">{detail.payroll_id}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Tenant ID</dt>
                    <dd className="font-mono font-medium text-gray-900">{detail.tenant_id}</dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Systémové</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Vytvorené</dt>
                    <dd className="font-medium text-gray-900">
                      {formatDateTime(detail.created_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Aktualizované</dt>
                    <dd className="font-medium text-gray-900">
                      {formatDateTime(detail.updated_at)}
                    </dd>
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
              {editing ? 'Upraviť výplatnú pásku' : 'Nová výplatná páska'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Period */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Rok</label>
                  <input
                    type="number"
                    required
                    readOnly={!!editing}
                    min={2000}
                    max={2100}
                    value={form.period_year}
                    onChange={(e) => updateField('period_year', e.target.value)}
                    className={`w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 ${editing ? 'bg-gray-100 text-gray-500' : ''}`}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Mesiac</label>
                  <select
                    required
                    disabled={!!editing}
                    value={form.period_month}
                    onChange={(e) => updateField('period_month', e.target.value)}
                    className={`w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 ${editing ? 'bg-gray-100 text-gray-500' : ''}`}
                  >
                    {Array.from({ length: 12 }, (_, i) => (
                      <option key={i + 1} value={String(i + 1)}>
                        {String(i + 1).padStart(2, '0')}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Payroll ID + Employee ID */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Payroll ID
                  </label>
                  <input
                    type="text"
                    required
                    readOnly={!!editing}
                    value={form.payroll_id}
                    onChange={(e) => updateField('payroll_id', e.target.value)}
                    placeholder="UUID"
                    className={`w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 ${editing ? 'bg-gray-100 text-gray-500' : ''}`}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Zamestnanec ID
                  </label>
                  <input
                    type="text"
                    required
                    readOnly={!!editing}
                    value={form.employee_id}
                    onChange={(e) => updateField('employee_id', e.target.value)}
                    placeholder="UUID"
                    className={`w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 ${editing ? 'bg-gray-100 text-gray-500' : ''}`}
                  />
                </div>
              </div>

              {/* PDF path + file size */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Cesta k PDF
                  </label>
                  <input
                    type="text"
                    required
                    value={form.pdf_path}
                    onChange={(e) => updateField('pdf_path', e.target.value)}
                    placeholder="/payslips/2026/01/employee.pdf"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Veľkosť (bytes)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={form.file_size_bytes}
                    onChange={(e) => updateField('file_size_bytes', e.target.value)}
                    placeholder="voliteľné"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Downloaded at (edit only) */}
              {editing && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Dátum stiahnutia (ISO)
                  </label>
                  <input
                    type="text"
                    value={form.downloaded_at}
                    onChange={(e) => updateField('downloaded_at', e.target.value)}
                    placeholder="voliteľné — napr. 2026-01-15T10:30:00"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              )}

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
              Naozaj chcete zmazať výplatnú pásku za obdobie{' '}
              <strong>{formatPeriod(deleting.period_year, deleting.period_month)}</strong> pre
              zamestnanca <strong>{deleting.employee_id.slice(0, 8)}...</strong>?
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

export default PaySlipsPage
