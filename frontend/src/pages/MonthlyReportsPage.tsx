import { useCallback, useEffect, useState } from 'react'
import type {
  MonthlyReportRead,
  MonthlyReportCreate,
  MonthlyReportUpdate,
  ReportType,
  ReportStatus,
  FileFormat,
} from '@/types/monthly-report'
import {
  listMonthlyReports,
  createMonthlyReport,
  updateMonthlyReport,
  deleteMonthlyReport,
} from '@/services/monthly-report.service'
import { authStore } from '@/stores/auth.store'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  sp_monthly: 'SP mesačný výkaz',
  zp_vszp: 'ZP VšZP',
  zp_dovera: 'ZP Dôvera',
  zp_union: 'ZP Union',
  tax_prehled: 'Daňový prehľad',
}

const STATUS_LABELS: Record<ReportStatus, string> = {
  generated: 'Vygenerovaný',
  submitted: 'Odoslaný',
  accepted: 'Prijatý',
  rejected: 'Zamietnutý',
}

const STATUS_COLORS: Record<ReportStatus, string> = {
  generated: 'bg-blue-100 text-blue-800',
  submitted: 'bg-yellow-100 text-yellow-800',
  accepted: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
}

const FILE_FORMAT_LABELS: Record<FileFormat, string> = {
  xml: 'XML',
  pdf: 'PDF',
}

// -- Empty form state --------------------------------------------------------
interface FormState {
  tenant_id: string
  period_year: string
  period_month: string
  report_type: ReportType | ''
  file_path: string
  file_format: FileFormat
  status: ReportStatus
  deadline_date: string
  institution: string
  submitted_at: string
  health_insurer_id: string
}

const EMPTY_FORM: FormState = {
  tenant_id: '',
  period_year: String(new Date().getFullYear()),
  period_month: String(new Date().getMonth() + 1),
  report_type: '',
  file_path: '',
  file_format: 'xml',
  status: 'generated',
  deadline_date: '',
  institution: '',
  submitted_at: '',
  health_insurer_id: '',
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): MonthlyReportCreate {
  return {
    tenant_id: form.tenant_id,
    period_year: Number(form.period_year),
    period_month: Number(form.period_month),
    report_type: form.report_type as ReportType,
    file_path: form.file_path,
    file_format: form.file_format,
    status: form.status,
    deadline_date: form.deadline_date,
    institution: form.institution,
    submitted_at: form.submitted_at || null,
    health_insurer_id: form.health_insurer_id || null,
  }
}

function toUpdatePayload(form: FormState, original: MonthlyReportRead): MonthlyReportUpdate {
  const payload: MonthlyReportUpdate = {}
  if (form.file_path !== original.file_path) payload.file_path = form.file_path || null
  if (form.file_format !== original.file_format) payload.file_format = form.file_format || null
  if (form.status !== original.status) payload.status = form.status || null
  if (form.deadline_date !== original.deadline_date) payload.deadline_date = form.deadline_date || null
  if (form.institution !== original.institution) payload.institution = form.institution || null
  const originalSubmittedAt = original.submitted_at ?? ''
  if (form.submitted_at !== originalSubmittedAt) payload.submitted_at = form.submitted_at || null
  const originalHealthInsurerId = original.health_insurer_id ?? ''
  if (form.health_insurer_id !== originalHealthInsurerId) payload.health_insurer_id = form.health_insurer_id || null
  return payload
}

function reportToForm(r: MonthlyReportRead): FormState {
  return {
    tenant_id: r.tenant_id,
    period_year: String(r.period_year),
    period_month: String(r.period_month),
    report_type: r.report_type,
    file_path: r.file_path,
    file_format: r.file_format,
    status: r.status,
    deadline_date: r.deadline_date,
    institution: r.institution,
    submitted_at: r.submitted_at ?? '',
    health_insurer_id: r.health_insurer_id ?? '',
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

function formatPeriod(year: number, month: number): string {
  return `${String(month).padStart(2, '0')}/${year}`
}

// -- Component ---------------------------------------------------------------
function MonthlyReportsPage() {
  // List state
  const [items, setItems] = useState<MonthlyReportRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail state
  const [detail, setDetail] = useState<MonthlyReportRead | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<MonthlyReportRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<MonthlyReportRead | null>(null)

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listMonthlyReports({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
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

  function openEdit(report: MonthlyReportRead) {
    setEditing(report)
    setForm(reportToForm(report))
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
        await updateMonthlyReport(editing.id, toUpdatePayload(form, editing))
      } else {
        await createMonthlyReport(toCreatePayload(form))
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
      await deleteMonthlyReport(deleting.id)
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
          <h1 className="text-2xl font-bold text-gray-900">Mesačné výkazy</h1>
          <p className="mt-1 text-sm text-gray-600">
            SP/ZP/DÚ výkazy pre štatutárne orgány
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nový výkaz
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
                Typ výkazu
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Inštitúcia
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Stav
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Formát
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Termín
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
              items.map((report) => (
                <tr key={report.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {formatPeriod(report.period_year, report.period_month)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {REPORT_TYPE_LABELS[report.report_type] ?? report.report_type}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {report.institution}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[report.status] ?? 'bg-gray-100 text-gray-600'}`}
                    >
                      {STATUS_LABELS[report.status] ?? report.status}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {FILE_FORMAT_LABELS[report.file_format] ?? report.file_format}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(report.deadline_date)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(report)}
                      className="mr-2 text-gray-600 hover:text-gray-800"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(report)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upraviť
                    </button>
                    <button
                      onClick={() => setDeleting(report)}
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
                Výkaz — {REPORT_TYPE_LABELS[detail.report_type] ?? detail.report_type} (
                {formatPeriod(detail.period_year, detail.period_month)})
              </h2>
            </div>

            <div className="space-y-4">
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Obdobie a typ</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Obdobie</dt>
                    <dd className="font-medium text-gray-900">
                      {formatPeriod(detail.period_year, detail.period_month)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Typ výkazu</dt>
                    <dd className="font-medium text-gray-900">
                      {REPORT_TYPE_LABELS[detail.report_type] ?? detail.report_type}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Inštitúcia</dt>
                    <dd className="font-medium text-gray-900">{detail.institution}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Stav</dt>
                    <dd>
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[detail.status] ?? 'bg-gray-100 text-gray-600'}`}
                      >
                        {STATUS_LABELS[detail.status] ?? detail.status}
                      </span>
                    </dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Súbor</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Cesta k súboru</dt>
                    <dd className="font-medium text-gray-900">{detail.file_path}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Formát</dt>
                    <dd className="font-medium text-gray-900">
                      {FILE_FORMAT_LABELS[detail.file_format] ?? detail.file_format}
                    </dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Termíny</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Termín odovzdania</dt>
                    <dd className="font-medium text-gray-900">
                      {formatDate(detail.deadline_date)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Odoslané dňa</dt>
                    <dd className="font-medium text-gray-900">
                      {formatDate(detail.submitted_at)}
                    </dd>
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
                  {detail.health_insurer_id && (
                    <div>
                      <dt className="text-gray-500">Zdravotná poisťovňa ID</dt>
                      <dd className="font-medium text-gray-900">{detail.health_insurer_id}</dd>
                    </div>
                  )}
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
              {editing ? 'Upraviť výkaz' : 'Nový mesačný výkaz'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Period — only for create */}
              {!editing && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Rok</label>
                    <input
                      type="number"
                      required
                      min={2000}
                      max={2100}
                      value={form.period_year}
                      onChange={(e) => updateField('period_year', e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Mesiac</label>
                    <select
                      required
                      value={form.period_month}
                      onChange={(e) => updateField('period_month', e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    >
                      {Array.from({ length: 12 }, (_, i) => (
                        <option key={i + 1} value={String(i + 1)}>
                          {String(i + 1).padStart(2, '0')}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {/* Report type — only for create */}
              {!editing && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Typ výkazu
                  </label>
                  <select
                    required
                    value={form.report_type}
                    onChange={(e) => updateField('report_type', e.target.value as ReportType | '')}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    <option value="">— Vyberte typ —</option>
                    {(Object.keys(REPORT_TYPE_LABELS) as ReportType[]).map((rt) => (
                      <option key={rt} value={rt}>
                        {REPORT_TYPE_LABELS[rt]}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Institution */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Inštitúcia</label>
                <input
                  type="text"
                  required
                  value={form.institution}
                  onChange={(e) => updateField('institution', e.target.value)}
                  placeholder="napr. Sociálna poisťovňa"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </div>

              {/* File path + format */}
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Cesta k súboru
                  </label>
                  <input
                    type="text"
                    required
                    value={form.file_path}
                    onChange={(e) => updateField('file_path', e.target.value)}
                    placeholder="napr. /reports/2026/01/sp_monthly.xml"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Formát</label>
                  <select
                    value={form.file_format}
                    onChange={(e) => updateField('file_format', e.target.value as FileFormat)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    {(Object.keys(FILE_FORMAT_LABELS) as FileFormat[]).map((ff) => (
                      <option key={ff} value={ff}>
                        {FILE_FORMAT_LABELS[ff]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Status + deadline */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Stav</label>
                  <select
                    value={form.status}
                    onChange={(e) => updateField('status', e.target.value as ReportStatus)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    {(Object.keys(STATUS_LABELS) as ReportStatus[]).map((s) => (
                      <option key={s} value={s}>
                        {STATUS_LABELS[s]}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Termín odovzdania
                  </label>
                  <input
                    type="date"
                    required
                    value={form.deadline_date}
                    onChange={(e) => updateField('deadline_date', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Submitted at + health insurer */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Odoslané dňa
                  </label>
                  <input
                    type="datetime-local"
                    value={form.submitted_at}
                    onChange={(e) => updateField('submitted_at', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Zdravotná poisťovňa ID
                  </label>
                  <input
                    type="text"
                    value={form.health_insurer_id}
                    onChange={(e) => updateField('health_insurer_id', e.target.value)}
                    placeholder="voliteľné"
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
              Naozaj chcete zmazať výkaz{' '}
              <strong>{REPORT_TYPE_LABELS[deleting.report_type] ?? deleting.report_type}</strong> za
              obdobie{' '}
              <strong>{formatPeriod(deleting.period_year, deleting.period_month)}</strong>?
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

export default MonthlyReportsPage
