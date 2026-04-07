import { useCallback, useEffect, useState } from 'react'
import type {
  PayrollRead,
  PayrollCreate,
  PayrollUpdate,
  PayrollStatus,
  LedgerSyncStatus,
} from '@/types/payroll'
import {
  listPayrolls,
  createPayroll,
  updatePayroll,
  deletePayroll,
} from '@/services/payroll.service'
import { listEmployees } from '@/services/employee.service'
import type { EmployeeRead } from '@/types/employee'
import { authStore } from '@/stores/auth.store'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 50

const STATUS_LABELS: Record<PayrollStatus, string> = {
  draft: 'Koncept',
  calculated: 'Vypočítaná',
  approved: 'Schválená',
  paid: 'Vyplatená',
}

const STATUS_COLORS: Record<PayrollStatus, string> = {
  draft: 'bg-gray-100 text-gray-800',
  calculated: 'bg-blue-100 text-blue-800',
  approved: 'bg-green-100 text-green-800',
  paid: 'bg-emerald-100 text-emerald-800',
}

const LEDGER_LABELS: Record<LedgerSyncStatus, string> = {
  pending: 'Čaká',
  synced: 'Synchronizované',
  error: 'Chyba',
}

const LEDGER_COLORS: Record<LedgerSyncStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  synced: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
}

// -- Empty form state --------------------------------------------------------
interface FormState {
  tenant_id: string
  employee_id: string
  contract_id: string
  period_year: string
  period_month: string
  status: PayrollStatus
  base_wage: string
  overtime_hours: string
  overtime_amount: string
  bonus_amount: string
  supplement_amount: string
  gross_wage: string
  sp_assessment_base: string
  sp_nemocenske: string
  sp_starobne: string
  sp_invalidne: string
  sp_nezamestnanost: string
  sp_employee_total: string
  zp_assessment_base: string
  zp_employee: string
  partial_tax_base: string
  nczd_applied: string
  tax_base: string
  tax_advance: string
  child_bonus: string
  tax_after_bonus: string
  net_wage: string
  sp_employer_nemocenske: string
  sp_employer_starobne: string
  sp_employer_invalidne: string
  sp_employer_nezamestnanost: string
  sp_employer_garancne: string
  sp_employer_rezervny: string
  sp_employer_kurzarbeit: string
  sp_employer_urazove: string
  sp_employer_total: string
  zp_employer: string
  total_employer_cost: string
  pillar2_amount: string
}

const EMPTY_FORM: FormState = {
  tenant_id: '',
  employee_id: '',
  contract_id: '',
  period_year: String(new Date().getFullYear()),
  period_month: String(new Date().getMonth() + 1),
  status: 'draft',
  base_wage: '0',
  overtime_hours: '0',
  overtime_amount: '0',
  bonus_amount: '0',
  supplement_amount: '0',
  gross_wage: '0',
  sp_assessment_base: '0',
  sp_nemocenske: '0',
  sp_starobne: '0',
  sp_invalidne: '0',
  sp_nezamestnanost: '0',
  sp_employee_total: '0',
  zp_assessment_base: '0',
  zp_employee: '0',
  partial_tax_base: '0',
  nczd_applied: '0',
  tax_base: '0',
  tax_advance: '0',
  child_bonus: '0',
  tax_after_bonus: '0',
  net_wage: '0',
  sp_employer_nemocenske: '0',
  sp_employer_starobne: '0',
  sp_employer_invalidne: '0',
  sp_employer_nezamestnanost: '0',
  sp_employer_garancne: '0',
  sp_employer_rezervny: '0',
  sp_employer_kurzarbeit: '0',
  sp_employer_urazove: '0',
  sp_employer_total: '0',
  zp_employer: '0',
  total_employer_cost: '0',
  pillar2_amount: '0',
}

// -- Helpers -----------------------------------------------------------------
function toNum(v: string): number {
  return Number(v) || 0
}

function toCreatePayload(form: FormState): PayrollCreate {
  return {
    tenant_id: form.tenant_id,
    employee_id: form.employee_id,
    contract_id: form.contract_id,
    period_year: toNum(form.period_year),
    period_month: toNum(form.period_month),
    status: form.status,
    base_wage: toNum(form.base_wage),
    overtime_hours: toNum(form.overtime_hours),
    overtime_amount: toNum(form.overtime_amount),
    bonus_amount: toNum(form.bonus_amount),
    supplement_amount: toNum(form.supplement_amount),
    gross_wage: toNum(form.gross_wage),
    sp_assessment_base: toNum(form.sp_assessment_base),
    sp_nemocenske: toNum(form.sp_nemocenske),
    sp_starobne: toNum(form.sp_starobne),
    sp_invalidne: toNum(form.sp_invalidne),
    sp_nezamestnanost: toNum(form.sp_nezamestnanost),
    sp_employee_total: toNum(form.sp_employee_total),
    zp_assessment_base: toNum(form.zp_assessment_base),
    zp_employee: toNum(form.zp_employee),
    partial_tax_base: toNum(form.partial_tax_base),
    nczd_applied: toNum(form.nczd_applied),
    tax_base: toNum(form.tax_base),
    tax_advance: toNum(form.tax_advance),
    child_bonus: toNum(form.child_bonus),
    tax_after_bonus: toNum(form.tax_after_bonus),
    net_wage: toNum(form.net_wage),
    sp_employer_nemocenske: toNum(form.sp_employer_nemocenske),
    sp_employer_starobne: toNum(form.sp_employer_starobne),
    sp_employer_invalidne: toNum(form.sp_employer_invalidne),
    sp_employer_nezamestnanost: toNum(form.sp_employer_nezamestnanost),
    sp_employer_garancne: toNum(form.sp_employer_garancne),
    sp_employer_rezervny: toNum(form.sp_employer_rezervny),
    sp_employer_kurzarbeit: toNum(form.sp_employer_kurzarbeit),
    sp_employer_urazove: toNum(form.sp_employer_urazove),
    sp_employer_total: toNum(form.sp_employer_total),
    zp_employer: toNum(form.zp_employer),
    total_employer_cost: toNum(form.total_employer_cost),
    pillar2_amount: toNum(form.pillar2_amount),
  }
}

function toUpdatePayload(form: FormState, original: PayrollRead): PayrollUpdate {
  const payload: PayrollUpdate = {}
  if (form.status !== original.status) payload.status = form.status
  if (toNum(form.base_wage) !== original.base_wage) payload.base_wage = toNum(form.base_wage)
  if (toNum(form.overtime_hours) !== original.overtime_hours)
    payload.overtime_hours = toNum(form.overtime_hours)
  if (toNum(form.overtime_amount) !== original.overtime_amount)
    payload.overtime_amount = toNum(form.overtime_amount)
  if (toNum(form.bonus_amount) !== original.bonus_amount)
    payload.bonus_amount = toNum(form.bonus_amount)
  if (toNum(form.supplement_amount) !== original.supplement_amount)
    payload.supplement_amount = toNum(form.supplement_amount)
  if (toNum(form.gross_wage) !== original.gross_wage) payload.gross_wage = toNum(form.gross_wage)
  if (toNum(form.sp_assessment_base) !== original.sp_assessment_base)
    payload.sp_assessment_base = toNum(form.sp_assessment_base)
  if (toNum(form.sp_nemocenske) !== original.sp_nemocenske)
    payload.sp_nemocenske = toNum(form.sp_nemocenske)
  if (toNum(form.sp_starobne) !== original.sp_starobne)
    payload.sp_starobne = toNum(form.sp_starobne)
  if (toNum(form.sp_invalidne) !== original.sp_invalidne)
    payload.sp_invalidne = toNum(form.sp_invalidne)
  if (toNum(form.sp_nezamestnanost) !== original.sp_nezamestnanost)
    payload.sp_nezamestnanost = toNum(form.sp_nezamestnanost)
  if (toNum(form.sp_employee_total) !== original.sp_employee_total)
    payload.sp_employee_total = toNum(form.sp_employee_total)
  if (toNum(form.zp_assessment_base) !== original.zp_assessment_base)
    payload.zp_assessment_base = toNum(form.zp_assessment_base)
  if (toNum(form.zp_employee) !== original.zp_employee)
    payload.zp_employee = toNum(form.zp_employee)
  if (toNum(form.partial_tax_base) !== original.partial_tax_base)
    payload.partial_tax_base = toNum(form.partial_tax_base)
  if (toNum(form.nczd_applied) !== original.nczd_applied)
    payload.nczd_applied = toNum(form.nczd_applied)
  if (toNum(form.tax_base) !== original.tax_base) payload.tax_base = toNum(form.tax_base)
  if (toNum(form.tax_advance) !== original.tax_advance)
    payload.tax_advance = toNum(form.tax_advance)
  if (toNum(form.child_bonus) !== original.child_bonus)
    payload.child_bonus = toNum(form.child_bonus)
  if (toNum(form.tax_after_bonus) !== original.tax_after_bonus)
    payload.tax_after_bonus = toNum(form.tax_after_bonus)
  if (toNum(form.net_wage) !== original.net_wage) payload.net_wage = toNum(form.net_wage)
  if (toNum(form.sp_employer_nemocenske) !== original.sp_employer_nemocenske)
    payload.sp_employer_nemocenske = toNum(form.sp_employer_nemocenske)
  if (toNum(form.sp_employer_starobne) !== original.sp_employer_starobne)
    payload.sp_employer_starobne = toNum(form.sp_employer_starobne)
  if (toNum(form.sp_employer_invalidne) !== original.sp_employer_invalidne)
    payload.sp_employer_invalidne = toNum(form.sp_employer_invalidne)
  if (toNum(form.sp_employer_nezamestnanost) !== original.sp_employer_nezamestnanost)
    payload.sp_employer_nezamestnanost = toNum(form.sp_employer_nezamestnanost)
  if (toNum(form.sp_employer_garancne) !== original.sp_employer_garancne)
    payload.sp_employer_garancne = toNum(form.sp_employer_garancne)
  if (toNum(form.sp_employer_rezervny) !== original.sp_employer_rezervny)
    payload.sp_employer_rezervny = toNum(form.sp_employer_rezervny)
  if (toNum(form.sp_employer_kurzarbeit) !== original.sp_employer_kurzarbeit)
    payload.sp_employer_kurzarbeit = toNum(form.sp_employer_kurzarbeit)
  if (toNum(form.sp_employer_urazove) !== original.sp_employer_urazove)
    payload.sp_employer_urazove = toNum(form.sp_employer_urazove)
  if (toNum(form.sp_employer_total) !== original.sp_employer_total)
    payload.sp_employer_total = toNum(form.sp_employer_total)
  if (toNum(form.zp_employer) !== original.zp_employer)
    payload.zp_employer = toNum(form.zp_employer)
  if (toNum(form.total_employer_cost) !== original.total_employer_cost)
    payload.total_employer_cost = toNum(form.total_employer_cost)
  if (toNum(form.pillar2_amount) !== original.pillar2_amount)
    payload.pillar2_amount = toNum(form.pillar2_amount)
  return payload
}

function payrollToForm(p: PayrollRead): FormState {
  return {
    tenant_id: p.tenant_id,
    employee_id: p.employee_id,
    contract_id: p.contract_id,
    period_year: String(p.period_year),
    period_month: String(p.period_month),
    status: p.status,
    base_wage: String(p.base_wage),
    overtime_hours: String(p.overtime_hours),
    overtime_amount: String(p.overtime_amount),
    bonus_amount: String(p.bonus_amount),
    supplement_amount: String(p.supplement_amount),
    gross_wage: String(p.gross_wage),
    sp_assessment_base: String(p.sp_assessment_base),
    sp_nemocenske: String(p.sp_nemocenske),
    sp_starobne: String(p.sp_starobne),
    sp_invalidne: String(p.sp_invalidne),
    sp_nezamestnanost: String(p.sp_nezamestnanost),
    sp_employee_total: String(p.sp_employee_total),
    zp_assessment_base: String(p.zp_assessment_base),
    zp_employee: String(p.zp_employee),
    partial_tax_base: String(p.partial_tax_base),
    nczd_applied: String(p.nczd_applied),
    tax_base: String(p.tax_base),
    tax_advance: String(p.tax_advance),
    child_bonus: String(p.child_bonus),
    tax_after_bonus: String(p.tax_after_bonus),
    net_wage: String(p.net_wage),
    sp_employer_nemocenske: String(p.sp_employer_nemocenske),
    sp_employer_starobne: String(p.sp_employer_starobne),
    sp_employer_invalidne: String(p.sp_employer_invalidne),
    sp_employer_nezamestnanost: String(p.sp_employer_nezamestnanost),
    sp_employer_garancne: String(p.sp_employer_garancne),
    sp_employer_rezervny: String(p.sp_employer_rezervny),
    sp_employer_kurzarbeit: String(p.sp_employer_kurzarbeit),
    sp_employer_urazove: String(p.sp_employer_urazove),
    sp_employer_total: String(p.sp_employer_total),
    zp_employer: String(p.zp_employer),
    total_employer_cost: String(p.total_employer_cost),
    pillar2_amount: String(p.pillar2_amount),
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

function formatPeriod(year: number, month: number): string {
  return `${String(month).padStart(2, '0')}/${year}`
}

function formatAmount(amount: number): string {
  return amount.toLocaleString('sk-SK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// -- Number input helper -----------------------------------------------------
function NumberField({
  label,
  value,
  onChange,
  step = '0.01',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  step?: string
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-gray-700">{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500"
      />
    </label>
  )
}

// -- Component ---------------------------------------------------------------
function PayrollPage() {
  // List state
  const [items, setItems] = useState<PayrollRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail state
  const [detail, setDetail] = useState<PayrollRead | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<PayrollRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<PayrollRead | null>(null)

  // Employee lookup
  const [employeeMap, setEmployeeMap] = useState<Record<string, EmployeeRead>>({})

  useEffect(() => {
    listEmployees({ skip: 0, limit: 1000 })
      .then((res) => {
        const map: Record<string, EmployeeRead> = {}
        for (const emp of res.items) {
          map[emp.id] = emp
        }
        setEmployeeMap(map)
      })
      .catch(() => {})
  }, [])

  function employeeName(id: string): string {
    const emp = employeeMap[id]
    return emp ? `${emp.last_name} ${emp.first_name}` : id.substring(0, 8) + '...'
  }

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listPayrolls({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
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

  function openEdit(item: PayrollRead) {
    setEditing(item)
    setForm(payrollToForm(item))
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
        await updatePayroll(editing.id, toUpdatePayload(form, editing))
      } else {
        await createPayroll(toCreatePayload(form))
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
      await deletePayroll(deleting.id)
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
          <h1 className="text-2xl font-bold text-gray-900">Mzdy</h1>
          <p className="mt-1 text-sm text-gray-600">Mesačné mzdové výpočty</p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nová mzda
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Detail modal */}
      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">
                Detail mzdy &mdash; {formatPeriod(detail.period_year, detail.period_month)}
              </h2>
              <button
                onClick={() => setDetail(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                &times;
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-500">Status:</span>{' '}
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[detail.status]}`}
                >
                  {STATUS_LABELS[detail.status]}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-500">Zamestnanec:</span>{' '}
                {detail.employee_id}
              </div>
              <div>
                <span className="font-medium text-gray-500">Zmluva ID:</span> {detail.contract_id}
              </div>
              <div>
                <span className="font-medium text-gray-500">Obdobie:</span>{' '}
                {formatPeriod(detail.period_year, detail.period_month)}
              </div>
            </div>

            <h3 className="mt-4 text-sm font-semibold text-gray-700">Hrubá mzda</h3>
            <div className="mt-1 grid grid-cols-3 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Základná mzda:</span>{' '}
                {formatAmount(detail.base_wage)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Nadčasy (h):</span> {detail.overtime_hours}
              </div>
              <div>
                <span className="text-gray-500">Nadčasy:</span>{' '}
                {formatAmount(detail.overtime_amount)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Bonus:</span>{' '}
                {formatAmount(detail.bonus_amount)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Príplatky:</span>{' '}
                {formatAmount(detail.supplement_amount)} &euro;
              </div>
              <div>
                <span className="font-medium text-gray-700">Hrubá mzda:</span>{' '}
                {formatAmount(detail.gross_wage)} &euro;
              </div>
            </div>

            <h3 className="mt-4 text-sm font-semibold text-gray-700">SP zamestnanec</h3>
            <div className="mt-1 grid grid-cols-3 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Nemocenské:</span>{' '}
                {formatAmount(detail.sp_nemocenske)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Starobné:</span>{' '}
                {formatAmount(detail.sp_starobne)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Invalidné:</span>{' '}
                {formatAmount(detail.sp_invalidne)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Nezamestnanosť:</span>{' '}
                {formatAmount(detail.sp_nezamestnanost)} &euro;
              </div>
              <div>
                <span className="font-medium text-gray-700">SP celkom:</span>{' '}
                {formatAmount(detail.sp_employee_total)} &euro;
              </div>
            </div>

            <h3 className="mt-4 text-sm font-semibold text-gray-700">ZP zamestnanec</h3>
            <div className="mt-1 grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">VZ:</span>{' '}
                {formatAmount(detail.zp_assessment_base)} &euro;
              </div>
              <div>
                <span className="font-medium text-gray-700">ZP zamestnanec:</span>{' '}
                {formatAmount(detail.zp_employee)} &euro;
              </div>
            </div>

            <h3 className="mt-4 text-sm font-semibold text-gray-700">Dan</h3>
            <div className="mt-1 grid grid-cols-3 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Čiastkový ZD:</span>{' '}
                {formatAmount(detail.partial_tax_base)} &euro;
              </div>
              <div>
                <span className="text-gray-500">NCZD:</span>{' '}
                {formatAmount(detail.nczd_applied)} &euro;
              </div>
              <div>
                <span className="text-gray-500">ZD:</span>{' '}
                {formatAmount(detail.tax_base)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Preddavok na daň:</span>{' '}
                {formatAmount(detail.tax_advance)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Detský bonus:</span>{' '}
                {formatAmount(detail.child_bonus)} &euro;
              </div>
              <div>
                <span className="font-medium text-gray-700">Daň po bonuse:</span>{' '}
                {formatAmount(detail.tax_after_bonus)} &euro;
              </div>
            </div>

            <h3 className="mt-4 text-sm font-semibold text-gray-700">Čistá mzda</h3>
            <div className="mt-1 text-lg font-bold text-primary-700">
              {formatAmount(detail.net_wage)} &euro;
            </div>

            <h3 className="mt-4 text-sm font-semibold text-gray-700">SP zamestnávateľ</h3>
            <div className="mt-1 grid grid-cols-3 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Nemocenské:</span>{' '}
                {formatAmount(detail.sp_employer_nemocenske)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Starobné:</span>{' '}
                {formatAmount(detail.sp_employer_starobne)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Invalidné:</span>{' '}
                {formatAmount(detail.sp_employer_invalidne)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Nezamestnanosť:</span>{' '}
                {formatAmount(detail.sp_employer_nezamestnanost)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Garančné:</span>{' '}
                {formatAmount(detail.sp_employer_garancne)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Rezervný:</span>{' '}
                {formatAmount(detail.sp_employer_rezervny)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Kurzarbeit:</span>{' '}
                {formatAmount(detail.sp_employer_kurzarbeit)} &euro;
              </div>
              <div>
                <span className="text-gray-500">Úrazové:</span>{' '}
                {formatAmount(detail.sp_employer_urazove)} &euro;
              </div>
              <div>
                <span className="font-medium text-gray-700">SP celkom:</span>{' '}
                {formatAmount(detail.sp_employer_total)} &euro;
              </div>
            </div>

            <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
              <div>
                <span className="text-gray-500">ZP zamestnávateľ:</span>{' '}
                {formatAmount(detail.zp_employer)} &euro;
              </div>
              <div>
                <span className="text-gray-500">II. pilier:</span>{' '}
                {formatAmount(detail.pillar2_amount)} &euro;
              </div>
              <div>
                <span className="font-medium text-gray-700">Náklady zamestnávateľa:</span>{' '}
                {formatAmount(detail.total_employer_cost)} &euro;
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Ledger sync:</span>{' '}
                {detail.ledger_sync_status ? (
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${LEDGER_COLORS[detail.ledger_sync_status]}`}
                  >
                    {LEDGER_LABELS[detail.ledger_sync_status]}
                  </span>
                ) : (
                  '\u2014'
                )}
              </div>
              <div>
                <span className="text-gray-500">Schválil:</span>{' '}
                {detail.approved_by ?? '\u2014'}
              </div>
              <div>
                <span className="text-gray-500">Vypočítané:</span>{' '}
                {formatDate(detail.calculated_at)}
              </div>
              <div>
                <span className="text-gray-500">Schválené:</span>{' '}
                {formatDate(detail.approved_at)}
              </div>
              <div>
                <span className="text-gray-500">Vytvorené:</span>{' '}
                {formatDate(detail.created_at)}
              </div>
              <div>
                <span className="text-gray-500">Aktualizované:</span>{' '}
                {formatDate(detail.updated_at)}
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setDetail(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zavrieť
              </button>
            </div>
          </div>
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
                Zamestnanec
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Status
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Hrubá mzda
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Čistá mzda
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Náklady zam.
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Vytvorené
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
                  Žiadne záznamy
                </td>
              </tr>
            )}
            {!loading &&
              items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
                    {formatPeriod(item.period_year, item.period_month)}
                  </td>
                  <td
                    className="max-w-[160px] truncate whitespace-nowrap px-4 py-3 text-sm text-gray-600"
                    title={item.employee_id}
                  >
                    {employeeName(item.employee_id)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[item.status]}`}
                    >
                      {STATUS_LABELS[item.status]}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-900">
                    {formatAmount(item.gross_wage)} &euro;
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-medium text-primary-700">
                    {formatAmount(item.net_wage)} &euro;
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-600">
                    {formatAmount(item.total_employer_cost)} &euro;
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                    {formatDate(item.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(item)}
                      className="mr-2 text-gray-600 hover:text-gray-900"
                      title="Detail"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(item)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upraviť
                    </button>
                    <button
                      onClick={() => setDeleting(item)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Zmazať
                    </button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-gray-600">
        <span>
          Celkom: {total} záznamov (strana {page + 1} / {totalPages})
        </span>
        <div className="flex gap-2">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            className="rounded border border-gray-300 px-3 py-1 disabled:opacity-50"
          >
            Predchádzajúca
          </button>
          <button
            disabled={page + 1 >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded border border-gray-300 px-3 py-1 disabled:opacity-50"
          >
            Nasledujúca
          </button>
        </div>
      </div>

      {/* Delete confirm */}
      {deleting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="text-lg font-bold text-gray-900">Potvrdenie zmazania</h2>
            <p className="mt-2 text-sm text-gray-600">
              Naozaj chcete zmazať mzdu za obdobie{' '}
              {formatPeriod(deleting.period_year, deleting.period_month)}?
            </p>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => setDeleting(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
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

      {/* Create / Edit modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-bold text-gray-900">
              {editing ? 'Upraviť mzdu' : 'Nová mzda'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Basic info */}
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-semibold text-gray-700">
                  Základné údaje
                </legend>
                <div className="mt-2 grid grid-cols-3 gap-4">
                  <label className="block">
                    <span className="mb-1 block text-sm font-medium text-gray-700">
                      Zamestnanec
                    </span>
                    <input
                      type="text"
                      required
                      value={form.employee_id}
                      onChange={(e) => updateField('employee_id', e.target.value)}
                      disabled={!!editing}
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 disabled:bg-gray-100"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-sm font-medium text-gray-700">
                      Zmluva ID
                    </span>
                    <input
                      type="text"
                      required
                      value={form.contract_id}
                      onChange={(e) => updateField('contract_id', e.target.value)}
                      disabled={!!editing}
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 disabled:bg-gray-100"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-sm font-medium text-gray-700">Status</span>
                    <select
                      value={form.status}
                      onChange={(e) => updateField('status', e.target.value as PayrollStatus)}
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    >
                      {(Object.keys(STATUS_LABELS) as PayrollStatus[]).map((s) => (
                        <option key={s} value={s}>
                          {STATUS_LABELS[s]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-sm font-medium text-gray-700">Rok</span>
                    <input
                      type="number"
                      required
                      min={2020}
                      max={2099}
                      value={form.period_year}
                      onChange={(e) => updateField('period_year', e.target.value)}
                      disabled={!!editing}
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 disabled:bg-gray-100"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-sm font-medium text-gray-700">Mesiac</span>
                    <input
                      type="number"
                      required
                      min={1}
                      max={12}
                      value={form.period_month}
                      onChange={(e) => updateField('period_month', e.target.value)}
                      disabled={!!editing}
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 disabled:bg-gray-100"
                    />
                  </label>
                </div>
              </fieldset>

              {/* Gross wage */}
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-semibold text-gray-700">Hrubá mzda</legend>
                <div className="mt-2 grid grid-cols-3 gap-4">
                  <NumberField
                    label="Základná mzda"
                    value={form.base_wage}
                    onChange={(v) => updateField('base_wage', v)}
                  />
                  <NumberField
                    label="Nadčasy (hodiny)"
                    value={form.overtime_hours}
                    onChange={(v) => updateField('overtime_hours', v)}
                    step="0.5"
                  />
                  <NumberField
                    label="Nadčasy (suma)"
                    value={form.overtime_amount}
                    onChange={(v) => updateField('overtime_amount', v)}
                  />
                  <NumberField
                    label="Bonus"
                    value={form.bonus_amount}
                    onChange={(v) => updateField('bonus_amount', v)}
                  />
                  <NumberField
                    label="Príplatky"
                    value={form.supplement_amount}
                    onChange={(v) => updateField('supplement_amount', v)}
                  />
                  <NumberField
                    label="Hrubá mzda"
                    value={form.gross_wage}
                    onChange={(v) => updateField('gross_wage', v)}
                  />
                </div>
              </fieldset>

              {/* SP employee */}
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-semibold text-gray-700">
                  SP zamestnanec
                </legend>
                <div className="mt-2 grid grid-cols-3 gap-4">
                  <NumberField
                    label="Vymeriavací základ"
                    value={form.sp_assessment_base}
                    onChange={(v) => updateField('sp_assessment_base', v)}
                  />
                  <NumberField
                    label="Nemocenské"
                    value={form.sp_nemocenske}
                    onChange={(v) => updateField('sp_nemocenske', v)}
                  />
                  <NumberField
                    label="Starobné"
                    value={form.sp_starobne}
                    onChange={(v) => updateField('sp_starobne', v)}
                  />
                  <NumberField
                    label="Invalidné"
                    value={form.sp_invalidne}
                    onChange={(v) => updateField('sp_invalidne', v)}
                  />
                  <NumberField
                    label="Nezamestnanosť"
                    value={form.sp_nezamestnanost}
                    onChange={(v) => updateField('sp_nezamestnanost', v)}
                  />
                  <NumberField
                    label="SP celkom"
                    value={form.sp_employee_total}
                    onChange={(v) => updateField('sp_employee_total', v)}
                  />
                </div>
              </fieldset>

              {/* ZP employee */}
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-semibold text-gray-700">
                  ZP zamestnanec
                </legend>
                <div className="mt-2 grid grid-cols-2 gap-4">
                  <NumberField
                    label="Vymeriavací základ"
                    value={form.zp_assessment_base}
                    onChange={(v) => updateField('zp_assessment_base', v)}
                  />
                  <NumberField
                    label="ZP zamestnanec"
                    value={form.zp_employee}
                    onChange={(v) => updateField('zp_employee', v)}
                  />
                </div>
              </fieldset>

              {/* Tax */}
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-semibold text-gray-700">Dan</legend>
                <div className="mt-2 grid grid-cols-3 gap-4">
                  <NumberField
                    label="Čiastkový základ dane"
                    value={form.partial_tax_base}
                    onChange={(v) => updateField('partial_tax_base', v)}
                  />
                  <NumberField
                    label="NCZD"
                    value={form.nczd_applied}
                    onChange={(v) => updateField('nczd_applied', v)}
                  />
                  <NumberField
                    label="Základ dane"
                    value={form.tax_base}
                    onChange={(v) => updateField('tax_base', v)}
                  />
                  <NumberField
                    label="Preddavok na daň"
                    value={form.tax_advance}
                    onChange={(v) => updateField('tax_advance', v)}
                  />
                  <NumberField
                    label="Detský bonus"
                    value={form.child_bonus}
                    onChange={(v) => updateField('child_bonus', v)}
                  />
                  <NumberField
                    label="Daň po bonuse"
                    value={form.tax_after_bonus}
                    onChange={(v) => updateField('tax_after_bonus', v)}
                  />
                </div>
              </fieldset>

              {/* Net wage */}
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-semibold text-gray-700">Čistá mzda</legend>
                <div className="mt-2">
                  <NumberField
                    label="Čistá mzda"
                    value={form.net_wage}
                    onChange={(v) => updateField('net_wage', v)}
                  />
                </div>
              </fieldset>

              {/* SP employer */}
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-semibold text-gray-700">
                  SP zamestnávateľ
                </legend>
                <div className="mt-2 grid grid-cols-3 gap-4">
                  <NumberField
                    label="Nemocenské"
                    value={form.sp_employer_nemocenske}
                    onChange={(v) => updateField('sp_employer_nemocenske', v)}
                  />
                  <NumberField
                    label="Starobné"
                    value={form.sp_employer_starobne}
                    onChange={(v) => updateField('sp_employer_starobne', v)}
                  />
                  <NumberField
                    label="Invalidné"
                    value={form.sp_employer_invalidne}
                    onChange={(v) => updateField('sp_employer_invalidne', v)}
                  />
                  <NumberField
                    label="Nezamestnanosť"
                    value={form.sp_employer_nezamestnanost}
                    onChange={(v) => updateField('sp_employer_nezamestnanost', v)}
                  />
                  <NumberField
                    label="Garančné"
                    value={form.sp_employer_garancne}
                    onChange={(v) => updateField('sp_employer_garancne', v)}
                  />
                  <NumberField
                    label="Rezervný fond"
                    value={form.sp_employer_rezervny}
                    onChange={(v) => updateField('sp_employer_rezervny', v)}
                  />
                  <NumberField
                    label="Kurzarbeit"
                    value={form.sp_employer_kurzarbeit}
                    onChange={(v) => updateField('sp_employer_kurzarbeit', v)}
                  />
                  <NumberField
                    label="Úrazové"
                    value={form.sp_employer_urazove}
                    onChange={(v) => updateField('sp_employer_urazove', v)}
                  />
                  <NumberField
                    label="SP celkom"
                    value={form.sp_employer_total}
                    onChange={(v) => updateField('sp_employer_total', v)}
                  />
                </div>
              </fieldset>

              {/* ZP employer + pillar2 + total */}
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-semibold text-gray-700">
                  ZP zamestnávateľ &amp; Doplnkové
                </legend>
                <div className="mt-2 grid grid-cols-3 gap-4">
                  <NumberField
                    label="ZP zamestnávateľ"
                    value={form.zp_employer}
                    onChange={(v) => updateField('zp_employer', v)}
                  />
                  <NumberField
                    label="II. pilier"
                    value={form.pillar2_amount}
                    onChange={(v) => updateField('pillar2_amount', v)}
                  />
                  <NumberField
                    label="Náklady zamestnávateľa"
                    value={form.total_employer_cost}
                    onChange={(v) => updateField('total_employer_cost', v)}
                  />
                </div>
              </fieldset>

              {/* Actions */}
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={closeModal}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
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
    </div>
  )
}

export default PayrollPage
