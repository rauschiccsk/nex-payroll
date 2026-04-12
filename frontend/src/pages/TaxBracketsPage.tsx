import { useCallback, useEffect, useState } from 'react'
import type { TaxBracketRead, TaxBracketCreate, TaxBracketUpdate } from '@/types/tax-bracket'
import {
  listTaxBrackets,
  createTaxBracket,
  updateTaxBracket,
  deleteTaxBracket,
} from '@/services/tax-bracket.service'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

// -- Empty form state --------------------------------------------------------
interface FormState {
  bracket_order: string
  min_amount: string
  max_amount: string
  rate_percent: string
  nczd_annual: string
  nczd_monthly: string
  nczd_reduction_threshold: string
  nczd_reduction_formula: string
  valid_from: string
  valid_to: string
}

const EMPTY_FORM: FormState = {
  bracket_order: '',
  min_amount: '',
  max_amount: '',
  rate_percent: '',
  nczd_annual: '',
  nczd_monthly: '',
  nczd_reduction_threshold: '',
  nczd_reduction_formula: '',
  valid_from: '',
  valid_to: '',
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): TaxBracketCreate {
  return {
    bracket_order: Number(form.bracket_order),
    min_amount: form.min_amount,
    max_amount: form.max_amount || null,
    rate_percent: form.rate_percent,
    nczd_annual: form.nczd_annual,
    nczd_monthly: form.nczd_monthly,
    nczd_reduction_threshold: form.nczd_reduction_threshold,
    nczd_reduction_formula: form.nczd_reduction_formula,
    valid_from: form.valid_from,
    valid_to: form.valid_to || null,
  }
}

function toUpdatePayload(form: FormState): TaxBracketUpdate {
  return {
    bracket_order: Number(form.bracket_order),
    min_amount: form.min_amount,
    max_amount: form.max_amount || null,
    rate_percent: form.rate_percent,
    nczd_annual: form.nczd_annual,
    nczd_monthly: form.nczd_monthly,
    nczd_reduction_threshold: form.nczd_reduction_threshold,
    nczd_reduction_formula: form.nczd_reduction_formula,
    valid_from: form.valid_from,
    valid_to: form.valid_to || null,
  }
}

function bracketToForm(b: TaxBracketRead): FormState {
  return {
    bracket_order: String(b.bracket_order),
    min_amount: String(b.min_amount),
    max_amount: b.max_amount != null ? String(b.max_amount) : '',
    rate_percent: String(b.rate_percent),
    nczd_annual: String(b.nczd_annual),
    nczd_monthly: String(b.nczd_monthly),
    nczd_reduction_threshold: String(b.nczd_reduction_threshold),
    nczd_reduction_formula: b.nczd_reduction_formula,
    valid_from: b.valid_from,
    valid_to: b.valid_to ?? '',
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

function formatCurrency(val: string | null): string {
  if (val == null) return '\u2014'
  const num = parseFloat(val)
  if (isNaN(num)) return val
  return num.toLocaleString('sk-SK', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' \u20AC'
}

function formatPercent(val: string): string {
  const num = parseFloat(val)
  if (isNaN(num)) return val + ' %'
  return num.toLocaleString('sk-SK', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' %'
}

// -- Component ---------------------------------------------------------------
function TaxBracketsPage() {
  // List state
  const [items, setItems] = useState<TaxBracketRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<TaxBracketRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<TaxBracketRead | null>(null)

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listTaxBrackets({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
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

  function openEdit(bracket: TaxBracketRead) {
    setEditing(bracket)
    setForm(bracketToForm(bracket))
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
        await updateTaxBracket(editing.id, toUpdatePayload(form))
      } else {
        await createTaxBracket(toCreatePayload(form))
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
      await deleteTaxBracket(deleting.id)
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
          <h1 className="text-2xl font-bold text-gray-900">Danove pasma</h1>
          <p className="mt-1 text-sm text-gray-600">
            Sprava danovych pasiem a NCZD parametrov
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nove pasmo
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
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                  Poradie
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Od sumy
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Do sumy
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Sadzba
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  NCZD rocne
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  NCZD mesacne
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Platnost od
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Platnost do
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Akcie
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {loading && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-sm text-gray-500">
                    Nacitavam...
                  </td>
                </tr>
              )}
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-sm text-gray-500">
                    Ziadne danove pasma
                  </td>
                </tr>
              )}
              {!loading &&
                items.map((bracket) => (
                  <tr key={bracket.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3 text-center text-sm font-medium text-gray-900">
                      {bracket.bracket_order}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                      {formatCurrency(bracket.min_amount)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                      {formatCurrency(bracket.max_amount)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                      {formatPercent(bracket.rate_percent)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                      {formatCurrency(bracket.nczd_annual)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                      {formatCurrency(bracket.nczd_monthly)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                      {formatDate(bracket.valid_from)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                      {formatDate(bracket.valid_to)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                      <button
                        onClick={() => openEdit(bracket)}
                        className="mr-2 text-primary-600 hover:text-primary-800"
                      >
                        Upravit
                      </button>
                      <button
                        onClick={() => setDeleting(bracket)}
                        className="text-red-600 hover:text-red-800"
                      >
                        Zmazat
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

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
          <div className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              {editing ? 'Upravit danove pasmo' : 'Nove danove pasmo'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Bracket Order + Rate Percent */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Poradie pasma</label>
                  <input
                    type="number"
                    required
                    min={1}
                    value={form.bracket_order}
                    onChange={(e) => updateField('bracket_order', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 1"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Sadzba dane (%)</label>
                  <input
                    type="number"
                    required
                    min={0}
                    max={100}
                    step="0.01"
                    value={form.rate_percent}
                    onChange={(e) => updateField('rate_percent', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 19.00"
                  />
                </div>
              </div>

              {/* Min Amount + Max Amount */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Minimalna suma</label>
                  <input
                    type="number"
                    required
                    min={0}
                    step="0.01"
                    value={form.min_amount}
                    onChange={(e) => updateField('min_amount', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 0.00"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Maximalna suma <span className="text-gray-400">(volitelne)</span>
                  </label>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={form.max_amount}
                    onChange={(e) => updateField('max_amount', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="prazdne = neobmedzene"
                  />
                </div>
              </div>

              {/* NCZD Annual + Monthly */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">NCZD rocne</label>
                  <input
                    type="number"
                    required
                    min={0}
                    step="0.01"
                    value={form.nczd_annual}
                    onChange={(e) => updateField('nczd_annual', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 5646.48"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">NCZD mesacne</label>
                  <input
                    type="number"
                    required
                    min={0}
                    step="0.01"
                    value={form.nczd_monthly}
                    onChange={(e) => updateField('nczd_monthly', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 470.54"
                  />
                </div>
              </div>

              {/* NCZD Reduction Threshold + Formula */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Prah znizenia NCZD</label>
                  <input
                    type="number"
                    required
                    min={0}
                    step="0.01"
                    value={form.nczd_reduction_threshold}
                    onChange={(e) => updateField('nczd_reduction_threshold', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 24952.06"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Formula znizenia</label>
                  <input
                    type="text"
                    required
                    value={form.nczd_reduction_formula}
                    onChange={(e) => updateField('nczd_reduction_formula', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 44.2 * ZM - ZD"
                  />
                </div>
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
              Naozaj chcete zmazat danove pasmo <strong>#{deleting.bracket_order}</strong> ({formatPercent(deleting.rate_percent)})?
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

export default TaxBracketsPage
