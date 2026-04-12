import { useCallback, useEffect, useState } from 'react'
import type {
  PaymentOrderRead,
  PaymentOrderCreate,
  PaymentOrderUpdate,
  PaymentType,
  PaymentStatus,
} from '@/types/payment-order'
import type { EmployeeRead } from '@/types/employee'
import type { HealthInsurerRead } from '@/types/health-insurer'
import {
  listPaymentOrders,
  createPaymentOrder,
  updatePaymentOrder,
  deletePaymentOrder,
} from '@/services/payment-order.service'
import { listEmployees } from '@/services/employee.service'
import { listHealthInsurers } from '@/services/health-insurer.service'
import { authStore } from '@/stores/auth.store'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

const PAYMENT_TYPE_LABELS: Record<PaymentType, string> = {
  net_wage: 'Čistá mzda',
  sp: 'Sociálna poisťovňa',
  zp_vszp: 'ZP VšZP',
  zp_dovera: 'ZP Dôvera',
  zp_union: 'ZP Union',
  tax: 'Daň z príjmu',
  pillar2: 'II. pilier',
}

const STATUS_LABELS: Record<PaymentStatus, string> = {
  pending: 'Čaká na export',
  exported: 'Exportovaný',
  paid: 'Zaplatený',
}

const STATUS_COLORS: Record<PaymentStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  exported: 'bg-blue-100 text-blue-800',
  paid: 'bg-green-100 text-green-800',
}

// -- Empty form state --------------------------------------------------------
interface FormState {
  tenant_id: string
  period_year: string
  period_month: string
  payment_type: PaymentType | ''
  recipient_name: string
  recipient_iban: string
  recipient_bic: string
  amount: string
  variable_symbol: string
  specific_symbol: string
  constant_symbol: string
  reference: string
  status: PaymentStatus
  employee_id: string
  health_insurer_id: string
}

const EMPTY_FORM: FormState = {
  tenant_id: '',
  period_year: String(new Date().getFullYear()),
  period_month: String(new Date().getMonth() + 1),
  payment_type: '',
  recipient_name: '',
  recipient_iban: '',
  recipient_bic: '',
  amount: '',
  variable_symbol: '',
  specific_symbol: '',
  constant_symbol: '',
  reference: '',
  status: 'pending',
  employee_id: '',
  health_insurer_id: '',
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): PaymentOrderCreate {
  return {
    tenant_id: form.tenant_id,
    period_year: Number(form.period_year),
    period_month: Number(form.period_month),
    payment_type: form.payment_type as PaymentType,
    recipient_name: form.recipient_name,
    recipient_iban: form.recipient_iban,
    recipient_bic: form.recipient_bic || null,
    amount: form.amount,
    variable_symbol: form.variable_symbol || null,
    specific_symbol: form.specific_symbol || null,
    constant_symbol: form.constant_symbol || null,
    reference: form.reference || null,
    status: form.status,
    employee_id: form.employee_id || null,
    health_insurer_id: form.health_insurer_id || null,
  }
}

function toUpdatePayload(form: FormState, original: PaymentOrderRead): PaymentOrderUpdate {
  const payload: PaymentOrderUpdate = {}
  if (form.recipient_name !== original.recipient_name)
    payload.recipient_name = form.recipient_name || null
  if (form.recipient_iban !== original.recipient_iban)
    payload.recipient_iban = form.recipient_iban || null
  const origBic = original.recipient_bic ?? ''
  if (form.recipient_bic !== origBic) payload.recipient_bic = form.recipient_bic || null
  if (form.amount !== original.amount) payload.amount = form.amount
  const origVs = original.variable_symbol ?? ''
  if (form.variable_symbol !== origVs) payload.variable_symbol = form.variable_symbol || null
  const origSs = original.specific_symbol ?? ''
  if (form.specific_symbol !== origSs) payload.specific_symbol = form.specific_symbol || null
  const origCs = original.constant_symbol ?? ''
  if (form.constant_symbol !== origCs) payload.constant_symbol = form.constant_symbol || null
  const origRef = original.reference ?? ''
  if (form.reference !== origRef) payload.reference = form.reference || null
  if (form.status !== original.status) payload.status = form.status || null
  const origEmpId = original.employee_id ?? ''
  if (form.employee_id !== origEmpId) payload.employee_id = form.employee_id || null
  const origHiId = original.health_insurer_id ?? ''
  if (form.health_insurer_id !== origHiId)
    payload.health_insurer_id = form.health_insurer_id || null
  return payload
}

function orderToForm(o: PaymentOrderRead): FormState {
  return {
    tenant_id: o.tenant_id,
    period_year: String(o.period_year),
    period_month: String(o.period_month),
    payment_type: o.payment_type,
    recipient_name: o.recipient_name,
    recipient_iban: o.recipient_iban,
    recipient_bic: o.recipient_bic ?? '',
    amount: String(o.amount),
    variable_symbol: o.variable_symbol ?? '',
    specific_symbol: o.specific_symbol ?? '',
    constant_symbol: o.constant_symbol ?? '',
    reference: o.reference ?? '',
    status: o.status,
    employee_id: o.employee_id ?? '',
    health_insurer_id: o.health_insurer_id ?? '',
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

function formatPeriod(year: number, month: number): string {
  return `${String(month).padStart(2, '0')}/${year}`
}

function formatAmount(amount: string): string {
  const num = parseFloat(amount)
  if (isNaN(num)) return '0,00'
  return num.toLocaleString('sk-SK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// -- Component ---------------------------------------------------------------
function PaymentsPage() {
  // List state
  const [items, setItems] = useState<PaymentOrderRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail state
  const [detail, setDetail] = useState<PaymentOrderRead | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<PaymentOrderRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<PaymentOrderRead | null>(null)

  // Reference data for dropdowns
  const [employees, setEmployees] = useState<EmployeeRead[]>([])
  const [healthInsurers, setHealthInsurers] = useState<HealthInsurerRead[]>([])

  useEffect(() => {
    listEmployees({ skip: 0, limit: 1000 })
      .then((res) => setEmployees(res.items))
      .catch(() => {})
    listHealthInsurers({ skip: 0, limit: 1000 })
      .then((res) => setHealthInsurers(res.items))
      .catch(() => {})
  }, [])

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listPaymentOrders({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
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

  function openEdit(order: PaymentOrderRead) {
    setEditing(order)
    setForm(orderToForm(order))
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
        await updatePaymentOrder(editing.id, toUpdatePayload(form, editing))
      } else {
        await createPaymentOrder(toCreatePayload(form))
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
      await deletePaymentOrder(deleting.id)
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

  // -- Helpers: resolve names ------------------------------------------------
  function employeeName(employeeId: string | null): string {
    if (!employeeId) return '\u2014'
    const emp = employees.find((e) => e.id === employeeId)
    if (emp) return `${emp.last_name} ${emp.first_name}`
    return employeeId.slice(0, 8) + '...'
  }

  function healthInsurerName(hiId: string | null): string {
    if (!hiId) return '\u2014'
    const hi = healthInsurers.find((h) => h.id === hiId)
    if (hi) return `${hi.name} (${hi.code})`
    return hiId.slice(0, 8) + '...'
  }

  // -- Render ----------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Platobné príkazy</h1>
          <p className="mt-1 text-sm text-gray-600">
            Správa platobných príkazov a SEPA export
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nový platobný príkaz
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
                Typ platby
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Príjemca
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                IBAN
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Suma
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
              items.map((order) => (
                <tr key={order.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {formatPeriod(order.period_year, order.period_month)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {PAYMENT_TYPE_LABELS[order.payment_type] ?? order.payment_type}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {order.recipient_name}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-mono text-gray-700">
                    {order.recipient_iban}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-medium text-gray-900">
                    {formatAmount(order.amount)} &euro;
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[order.status] ?? 'bg-gray-100 text-gray-600'}`}
                    >
                      {STATUS_LABELS[order.status] ?? order.status}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(order)}
                      className="mr-2 text-gray-600 hover:text-gray-800"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(order)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upraviť
                    </button>
                    <button
                      onClick={() => setDeleting(order)}
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
                Platobný príkaz — {PAYMENT_TYPE_LABELS[detail.payment_type] ?? detail.payment_type}{' '}
                ({formatPeriod(detail.period_year, detail.period_month)})
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
                    <dt className="text-gray-500">Typ platby</dt>
                    <dd className="font-medium text-gray-900">
                      {PAYMENT_TYPE_LABELS[detail.payment_type] ?? detail.payment_type}
                    </dd>
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
                  <div>
                    <dt className="text-gray-500">Suma</dt>
                    <dd className="font-medium text-gray-900">
                      {formatAmount(detail.amount)} &euro;
                    </dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Príjemca</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div className="col-span-2">
                    <dt className="text-gray-500">Názov</dt>
                    <dd className="font-medium text-gray-900">{detail.recipient_name}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">IBAN</dt>
                    <dd className="font-mono font-medium text-gray-900">
                      {detail.recipient_iban}
                    </dd>
                  </div>
                  {detail.recipient_bic && (
                    <div>
                      <dt className="text-gray-500">BIC/SWIFT</dt>
                      <dd className="font-mono font-medium text-gray-900">
                        {detail.recipient_bic}
                      </dd>
                    </div>
                  )}
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">
                  Symboly a referencia
                </legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Variabilný symbol</dt>
                    <dd className="font-medium text-gray-900">
                      {detail.variable_symbol || '\u2014'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Špecifický symbol</dt>
                    <dd className="font-medium text-gray-900">
                      {detail.specific_symbol || '\u2014'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Konštantný symbol</dt>
                    <dd className="font-medium text-gray-900">
                      {detail.constant_symbol || '\u2014'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">SEPA referencia</dt>
                    <dd className="font-medium text-gray-900">{detail.reference || '\u2014'}</dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Väzby a systém</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  {detail.employee_id && (
                    <div>
                      <dt className="text-gray-500">Zamestnanec</dt>
                      <dd className="font-medium text-gray-900">
                        {employeeName(detail.employee_id)}
                      </dd>
                    </div>
                  )}
                  {detail.health_insurer_id && (
                    <div>
                      <dt className="text-gray-500">Zdravotná poisťovňa</dt>
                      <dd className="font-medium text-gray-900">
                        {healthInsurerName(detail.health_insurer_id)}
                      </dd>
                    </div>
                  )}
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
              {editing ? 'Upraviť platobný príkaz' : 'Nový platobný príkaz'}
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

              {/* Payment type — only for create */}
              {!editing && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Typ platby
                  </label>
                  <select
                    required
                    value={form.payment_type}
                    onChange={(e) =>
                      updateField('payment_type', e.target.value as PaymentType | '')
                    }
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    <option value="">— Vyberte typ —</option>
                    {(Object.keys(PAYMENT_TYPE_LABELS) as PaymentType[]).map((pt) => (
                      <option key={pt} value={pt}>
                        {PAYMENT_TYPE_LABELS[pt]}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Recipient name + IBAN */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Názov príjemcu
                  </label>
                  <input
                    type="text"
                    required
                    value={form.recipient_name}
                    onChange={(e) => updateField('recipient_name', e.target.value)}
                    placeholder="napr. Sociálna poisťovňa"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">IBAN</label>
                  <input
                    type="text"
                    required
                    maxLength={34}
                    value={form.recipient_iban}
                    onChange={(e) => updateField('recipient_iban', e.target.value)}
                    placeholder="SK..."
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* BIC + Amount */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">BIC/SWIFT</label>
                  <input
                    type="text"
                    maxLength={11}
                    value={form.recipient_bic}
                    onChange={(e) => updateField('recipient_bic', e.target.value)}
                    placeholder="voliteľné"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Suma (EUR)</label>
                  <input
                    type="number"
                    required
                    min={0}
                    step="0.01"
                    value={form.amount}
                    onChange={(e) => updateField('amount', e.target.value)}
                    placeholder="0.00"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Symbols */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">VS</label>
                  <input
                    type="text"
                    maxLength={10}
                    value={form.variable_symbol}
                    onChange={(e) => updateField('variable_symbol', e.target.value)}
                    placeholder="voliteľné"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">ŠS</label>
                  <input
                    type="text"
                    maxLength={10}
                    value={form.specific_symbol}
                    onChange={(e) => updateField('specific_symbol', e.target.value)}
                    placeholder="voliteľné"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">KS</label>
                  <input
                    type="text"
                    maxLength={4}
                    value={form.constant_symbol}
                    onChange={(e) => updateField('constant_symbol', e.target.value)}
                    placeholder="voliteľné"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Reference + Status */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    SEPA referencia
                  </label>
                  <input
                    type="text"
                    maxLength={140}
                    value={form.reference}
                    onChange={(e) => updateField('reference', e.target.value)}
                    placeholder="voliteľné"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Stav</label>
                  <select
                    value={form.status}
                    onChange={(e) => updateField('status', e.target.value as PaymentStatus)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    {(Object.keys(STATUS_LABELS) as PaymentStatus[]).map((s) => (
                      <option key={s} value={s}>
                        {STATUS_LABELS[s]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Employee + Health insurer */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Zamestnanec
                  </label>
                  <select
                    value={form.employee_id}
                    onChange={(e) => updateField('employee_id', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    <option value="">— Žiadny —</option>
                    {employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.last_name} {emp.first_name} ({emp.employee_number})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Zdravotná poisťovňa
                  </label>
                  <select
                    value={form.health_insurer_id}
                    onChange={(e) => updateField('health_insurer_id', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    <option value="">— Žiadna —</option>
                    {healthInsurers.map((hi) => (
                      <option key={hi.id} value={hi.id}>
                        {hi.name} ({hi.code})
                      </option>
                    ))}
                  </select>
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
              Naozaj chcete zmazať platobný príkaz{' '}
              <strong>
                {PAYMENT_TYPE_LABELS[deleting.payment_type] ?? deleting.payment_type}
              </strong>{' '}
              pre <strong>{deleting.recipient_name}</strong> za obdobie{' '}
              <strong>{formatPeriod(deleting.period_year, deleting.period_month)}</strong> (
              {formatAmount(deleting.amount)} &euro;)?
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

export default PaymentsPage
