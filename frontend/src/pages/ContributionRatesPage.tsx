import { useCallback, useEffect, useState } from 'react'
import type { ContributionRateRead, ContributionRateCreate, ContributionRateUpdate, ContributionPayer } from '@/types/contribution-rate'
import {
  listContributionRates,
  createContributionRate,
  updateContributionRate,
  deleteContributionRate,
} from '@/services/contribution-rate.service'

// ── Constants ──────────────────────────────────────────────────
const PAGE_SIZE = 20

const FUND_OPTIONS = [
  'nemocenske',
  'starobne',
  'invalidne',
  'nezamestnanost',
  'garancne',
  'rezervny',
  'kurzarbeit',
  'urazove',
  'zdravotne',
] as const

const PAYER_OPTIONS: ContributionPayer[] = ['employee', 'employer']

const FUND_LABELS: Record<string, string> = {
  nemocenske: 'Nemocenské poistenie',
  starobne: 'Starobné poistenie',
  invalidne: 'Invalidné poistenie',
  nezamestnanost: 'Poistenie v nezamestnanosti',
  garancne: 'Garančné poistenie',
  rezervny: 'Rezervný fond',
  kurzarbeit: 'Kurzarbeit',
  urazove: 'Úrazové poistenie',
  zdravotne: 'Zdravotné poistenie',
}

const PAYER_LABELS: Record<ContributionPayer, string> = {
  employee: 'Zamestnanec',
  employer: 'Zamestnávateľ',
}

// ── Empty form state ────────────────────────────────────────────
interface FormState {
  rate_type: string
  rate_percent: string
  max_assessment_base: string
  payer: ContributionPayer
  fund: string
  valid_from: string
  valid_to: string
}

const EMPTY_FORM: FormState = {
  rate_type: '',
  rate_percent: '',
  max_assessment_base: '',
  payer: 'employee',
  fund: FUND_OPTIONS[0],
  valid_from: '',
  valid_to: '',
}

// ── Helpers ──────────────────────────────────────────────────
function toCreatePayload(form: FormState): ContributionRateCreate {
  return {
    rate_type: form.rate_type,
    rate_percent: form.rate_percent,
    max_assessment_base: form.max_assessment_base || null,
    payer: form.payer,
    fund: form.fund,
    valid_from: form.valid_from,
    valid_to: form.valid_to || null,
  }
}

function toUpdatePayload(form: FormState): ContributionRateUpdate {
  return {
    rate_type: form.rate_type,
    rate_percent: form.rate_percent,
    max_assessment_base: form.max_assessment_base || null,
    payer: form.payer,
    fund: form.fund,
    valid_from: form.valid_from,
    valid_to: form.valid_to || null,
  }
}

function rateToForm(rate: ContributionRateRead): FormState {
  return {
    rate_type: rate.rate_type,
    rate_percent: String(rate.rate_percent),
    max_assessment_base: rate.max_assessment_base != null ? String(rate.max_assessment_base) : '',
    payer: rate.payer,
    fund: rate.fund,
    valid_from: rate.valid_from,
    valid_to: rate.valid_to ?? '',
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('sk-SK')
}

function formatPercent(value: string): string {
  const num = parseFloat(value)
  return isNaN(num) ? `${value} %` : `${num.toFixed(2)} %`
}

function formatCurrency(value: string | null): string {
  if (value == null) return '—'
  const num = parseFloat(value)
  if (isNaN(num)) return value
  return new Intl.NumberFormat('sk-SK', { style: 'currency', currency: 'EUR' }).format(num)
}

// ── Component ──────────────────────────────────────────────────
function ContributionRatesPage() {
  // List state
  const [items, setItems] = useState<ContributionRateRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<ContributionRateRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<ContributionRateRead | null>(null)

  // ── Fetch ──────────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listContributionRates({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
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

  // ── Modal handlers ─────────────────────────────────────────
  function openCreate() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(rate: ContributionRateRead) {
    setEditing(rate)
    setForm(rateToForm(rate))
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
        await updateContributionRate(editing.id, toUpdatePayload(form))
      } else {
        await createContributionRate(toCreatePayload(form))
      }
      closeModal()
      await fetchData()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Chyba pri ukladaní')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Delete handlers ────────────────────────────────────────
  async function handleDelete() {
    if (!deleting) return
    try {
      await deleteContributionRate(deleting.id)
      setDeleting(null)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri mazaní')
      setDeleting(null)
    }
  }

  // ── Form field updater ────────────────────────────────────
  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // ── Render ─────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sadzby odvodov</h1>
          <p className="mt-1 text-sm text-gray-600">
            Správa sadzieb odvodov do fondov sociálneho a zdravotného poistenia
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nová sadzba
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
                Fond
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Platca
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Sadzba
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Max. VZ
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Platnosť od
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Platnosť do
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
                  Žiadne sadzby odvodov
                </td>
              </tr>
            )}
            {!loading &&
              items.map((rate) => (
                <tr key={rate.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {rate.rate_type}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {FUND_LABELS[rate.fund] ?? rate.fund}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        rate.payer === 'employee'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-green-100 text-green-800'
                      }`}
                    >
                      {PAYER_LABELS[rate.payer]}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                    {formatPercent(rate.rate_percent)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                    {formatCurrency(rate.max_assessment_base)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(rate.valid_from)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(rate.valid_to)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => openEdit(rate)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upraviť
                    </button>
                    <button
                      onClick={() => setDeleting(rate)}
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
              Zobrazených {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} z {total}
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

      {/* ── Create/Edit Modal ─────────────────────────────────── */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              {editing ? 'Upraviť sadzbu' : 'Nová sadzba odvodu'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Rate type */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Typ sadzby</label>
                <input
                  type="text"
                  required
                  value={form.rate_type}
                  onChange={(e) => updateField('rate_type', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="napr. standard"
                />
              </div>

              {/* Fund */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Fond</label>
                <select
                  required
                  value={form.fund}
                  onChange={(e) => updateField('fund', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  {FUND_OPTIONS.map((f) => (
                    <option key={f} value={f}>
                      {FUND_LABELS[f] ?? f}
                    </option>
                  ))}
                </select>
              </div>

              {/* Payer */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Platca</label>
                <select
                  required
                  value={form.payer}
                  onChange={(e) => updateField('payer', e.target.value as ContributionPayer)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  {PAYER_OPTIONS.map((p) => (
                    <option key={p} value={p}>
                      {PAYER_LABELS[p]}
                    </option>
                  ))}
                </select>
              </div>

              {/* Rate percent + Max assessment base (side by side) */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Sadzba (%)
                  </label>
                  <input
                    type="number"
                    required
                    step="0.01"
                    min="0"
                    max="100"
                    value={form.rate_percent}
                    onChange={(e) => updateField('rate_percent', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 4.00"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Max. VZ (EUR)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.max_assessment_base}
                    onChange={(e) => updateField('max_assessment_base', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="voliteľné"
                  />
                </div>
              </div>

              {/* Valid from / to */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Platnosť od
                  </label>
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
                    Platnosť do
                  </label>
                  <input
                    type="date"
                    value={form.valid_to}
                    onChange={(e) => updateField('valid_to', e.target.value)}
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

      {/* ── Delete Confirmation ───────────────────────────────── */}
      {deleting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">Potvrdiť zmazanie</h2>
            <p className="mb-4 text-sm text-gray-600">
              Naozaj chcete zmazať sadzbu <strong>{deleting.rate_type}</strong> (
              {FUND_LABELS[deleting.fund] ?? deleting.fund}, {PAYER_LABELS[deleting.payer]})?
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

export default ContributionRatesPage
