import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import type { PayrollRead, PayrollStatus, LedgerSyncStatus } from '@/types/payroll'
import {
  getPayroll,
  calculatePayroll,
  approvePayroll,
  updatePayroll,
} from '@/services/payroll.service'
import { listEmployees } from '@/services/employee.service'
import type { EmployeeRead } from '@/types/employee'

// -- Constants ---------------------------------------------------------------
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

const MONTH_NAMES = [
  '',
  'Január',
  'Február',
  'Marec',
  'Apríl',
  'Máj',
  'Jún',
  'Júl',
  'August',
  'September',
  'Október',
  'November',
  'December',
]

const EMPLOYEE_FETCH_LIMIT = 1000

// Fields that are user-editable inputs (not computed by payroll engine)
const EDITABLE_FIELDS = new Set([
  'base_wage',
  'overtime_hours',
  'overtime_amount',
  'bonus_amount',
  'supplement_amount',
])

// -- Helpers -----------------------------------------------------------------
function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

function formatAmount(amount: string): string {
  const n = parseFloat(amount) || 0
  return n.toLocaleString('sk-SK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// -- Number field helper -----------------------------------------------------
function NumberField({
  label,
  value,
  onChange,
  step = '0.01',
  disabled = false,
}: {
  label: string
  value: string | undefined
  onChange: (v: string) => void
  step?: string
  disabled?: boolean
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-gray-700">{label}</span>
      <input
        type="number"
        step={step}
        value={value ?? '0'}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500 disabled:bg-gray-100"
      />
    </label>
  )
}

// -- Amount row helper -------------------------------------------------------
function AmountRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-gray-100 py-2">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="text-sm font-medium text-gray-900">{formatAmount(value)} &euro;</span>
    </div>
  )
}

// -- Component ---------------------------------------------------------------
function PayrollDetailPage() {
  const { year, month, id } = useParams<{ year: string; month: string; id: string }>()
  const navigate = useNavigate()
  const periodYear = Number(year)
  const periodMonth = Number(month)

  const [payroll, setPayroll] = useState<PayrollRead | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  // Edit mode
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Employee lookup
  const [employeeMap, setEmployeeMap] = useState<Record<string, EmployeeRead>>({})

  useEffect(() => {
    listEmployees({ skip: 0, limit: EMPLOYEE_FETCH_LIMIT })
      .then((res) => {
        const map: Record<string, EmployeeRead> = {}
        for (const emp of res.items) {
          map[emp.id] = emp
        }
        setEmployeeMap(map)
      })
      .catch((err) => {
        console.warn('Failed to load employees for lookup:', err)
      })
  }, [])

  function employeeName(empId: string): string {
    const emp = employeeMap[empId]
    return emp ? `${emp.last_name} ${emp.first_name}` : empId.substring(0, 8) + '...'
  }

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const data = await getPayroll(id)
      setPayroll(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nepodarilo sa načítať dáta')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // -- Actions ---------------------------------------------------------------
  async function handleCalculate() {
    if (!payroll) return
    setActionLoading(true)
    try {
      const updated = await calculatePayroll(payroll.id)
      setPayroll(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri výpočte')
    } finally {
      setActionLoading(false)
    }
  }

  async function handleApprove() {
    if (!payroll) return
    setActionLoading(true)
    try {
      const updated = await approvePayroll(payroll.id)
      setPayroll(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri schvaľovaní')
    } finally {
      setActionLoading(false)
    }
  }

  // -- Edit mode -------------------------------------------------------------
  function startEdit() {
    if (!payroll) return
    // Only editable input fields + computed fields for display (disabled in form)
    setEditForm({
      // Editable input fields
      base_wage: String(payroll.base_wage),
      overtime_hours: String(payroll.overtime_hours),
      overtime_amount: String(payroll.overtime_amount),
      bonus_amount: String(payroll.bonus_amount),
      supplement_amount: String(payroll.supplement_amount),
      // Computed fields (displayed as disabled/read-only)
      gross_wage: String(payroll.gross_wage),
      sp_assessment_base: String(payroll.sp_assessment_base),
      sp_nemocenske: String(payroll.sp_nemocenske),
      sp_starobne: String(payroll.sp_starobne),
      sp_invalidne: String(payroll.sp_invalidne),
      sp_nezamestnanost: String(payroll.sp_nezamestnanost),
      sp_employee_total: String(payroll.sp_employee_total),
      zp_assessment_base: String(payroll.zp_assessment_base),
      zp_employee: String(payroll.zp_employee),
      partial_tax_base: String(payroll.partial_tax_base),
      nczd_applied: String(payroll.nczd_applied),
      tax_base: String(payroll.tax_base),
      tax_advance: String(payroll.tax_advance),
      child_bonus: String(payroll.child_bonus),
      tax_after_bonus: String(payroll.tax_after_bonus),
      net_wage: String(payroll.net_wage),
      sp_employer_nemocenske: String(payroll.sp_employer_nemocenske),
      sp_employer_starobne: String(payroll.sp_employer_starobne),
      sp_employer_invalidne: String(payroll.sp_employer_invalidne),
      sp_employer_nezamestnanost: String(payroll.sp_employer_nezamestnanost),
      sp_employer_garancne: String(payroll.sp_employer_garancne),
      sp_employer_rezervny: String(payroll.sp_employer_rezervny),
      sp_employer_kurzarbeit: String(payroll.sp_employer_kurzarbeit),
      sp_employer_urazove: String(payroll.sp_employer_urazove),
      sp_employer_total: String(payroll.sp_employer_total),
      zp_employer: String(payroll.zp_employer),
      total_employer_cost: String(payroll.total_employer_cost),
      pillar2_amount: String(payroll.pillar2_amount),
    })
    setSaveError(null)
    setEditMode(true)
  }

  async function handleSave() {
    if (!payroll) return
    setSaving(true)
    setSaveError(null)
    try {
      const payload: Record<string, string> = {}
      // Only send editable (input) fields, never computed fields
      for (const key of Object.keys(editForm)) {
        if (!EDITABLE_FIELDS.has(key)) continue
        const original = String(payroll[key as keyof PayrollRead])
        if (editForm[key] !== original) {
          payload[key] = editForm[key] ?? ''
        }
      }
      if (Object.keys(payload).length > 0) {
        const updated = await updatePayroll(payroll.id, payload)
        setPayroll(updated)
      }
      setEditMode(false)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Chyba pri ukladaní')
    } finally {
      setSaving(false)
    }
  }

  function updateEditField(key: string, value: string) {
    setEditForm((prev) => ({ ...prev, [key]: value }))
  }

  // -- Loading / Error states ------------------------------------------------
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500">Načítavam...</p>
      </div>
    )
  }

  if (error && !payroll) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
        <button
          onClick={() => navigate(`/payroll/${year}/${month}`)}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          &larr; Späť
        </button>
      </div>
    )
  }

  if (!payroll) return null

  // -- Render - Read mode ----------------------------------------------------
  if (!editMode) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Detail mzdy &mdash; {MONTH_NAMES[periodMonth]} {periodYear}
            </h1>
            <p className="mt-1 text-sm text-gray-600">{employeeName(payroll.employee_id)}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigate(`/payroll/${year}/${month}`)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              &larr; Späť
            </button>
            {payroll.status === 'draft' && (
              <>
                <button
                  onClick={startEdit}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                >
                  Upraviť
                </button>
                <button
                  onClick={handleCalculate}
                  disabled={actionLoading}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionLoading ? 'Vypočítavam...' : 'Vypočítať'}
                </button>
              </>
            )}
            {payroll.status === 'calculated' && (
              <button
                onClick={handleApprove}
                disabled={actionLoading}
                className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {actionLoading ? 'Schvaľujem...' : 'Schváliť'}
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Status & info card */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="grid grid-cols-4 gap-6">
            <div>
              <span className="text-xs font-medium uppercase text-gray-500">Status</span>
              <div className="mt-1">
                <span
                  className={`inline-block rounded-full px-3 py-1 text-sm font-medium ${STATUS_COLORS[payroll.status]}`}
                >
                  {STATUS_LABELS[payroll.status]}
                </span>
              </div>
            </div>
            <div>
              <span className="text-xs font-medium uppercase text-gray-500">Zamestnanec</span>
              <p className="mt-1 text-sm font-medium text-gray-900">
                {employeeName(payroll.employee_id)}
              </p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase text-gray-500">Zmluva</span>
              <p className="mt-1 text-sm text-gray-600">
                {payroll.contract_id.substring(0, 8)}...
              </p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase text-gray-500">Ledger sync</span>
              <div className="mt-1">
                {payroll.ledger_sync_status ? (
                  <span
                    className={`inline-block rounded-full px-3 py-1 text-sm font-medium ${LEDGER_COLORS[payroll.ledger_sync_status]}`}
                  >
                    {LEDGER_LABELS[payroll.ledger_sync_status]}
                  </span>
                ) : (
                  <span className="text-sm text-gray-400">&mdash;</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Net wage highlight */}
        <div className="rounded-lg border border-primary-200 bg-primary-50 p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-lg font-medium text-primary-800">Čistá mzda</span>
            <span className="text-3xl font-bold text-primary-700">
              {formatAmount(payroll.net_wage)} &euro;
            </span>
          </div>
        </div>

        {/* Detail sections in grid */}
        <div className="grid grid-cols-2 gap-6">
          {/* Gross wage */}
          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">Hrubá mzda</h3>
            <AmountRow label="Základná mzda" value={payroll.base_wage} />
            <div className="flex items-center justify-between border-b border-gray-100 py-2">
              <span className="text-sm text-gray-600">Nadčasy ({payroll.overtime_hours} h)</span>
              <span className="text-sm font-medium text-gray-900">
                {formatAmount(payroll.overtime_amount)} &euro;
              </span>
            </div>
            <AmountRow label="Bonus" value={payroll.bonus_amount} />
            <AmountRow label="Príplatky" value={payroll.supplement_amount} />
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm font-semibold text-gray-800">Hrubá mzda</span>
              <span className="text-sm font-bold text-gray-900">
                {formatAmount(payroll.gross_wage)} &euro;
              </span>
            </div>
          </div>

          {/* Tax */}
          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">Daň</h3>
            <AmountRow label="Čiastkový základ dane" value={payroll.partial_tax_base} />
            <AmountRow label="NCZD" value={payroll.nczd_applied} />
            <AmountRow label="Základ dane" value={payroll.tax_base} />
            <AmountRow label="Preddavok na daň" value={payroll.tax_advance} />
            <AmountRow label="Detský bonus" value={payroll.child_bonus} />
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm font-semibold text-gray-800">Daň po bonuse</span>
              <span className="text-sm font-bold text-gray-900">
                {formatAmount(payroll.tax_after_bonus)} &euro;
              </span>
            </div>
          </div>

          {/* SP employee */}
          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">SP zamestnanec</h3>
            <AmountRow
              label="Vymeriavací základ"
              value={payroll.sp_assessment_base}
            />
            <AmountRow label="Nemocenské" value={payroll.sp_nemocenske} />
            <AmountRow label="Starobné" value={payroll.sp_starobne} />
            <AmountRow label="Invalidné" value={payroll.sp_invalidne} />
            <AmountRow label="Nezamestnanosť" value={payroll.sp_nezamestnanost} />
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm font-semibold text-gray-800">SP celkom</span>
              <span className="text-sm font-bold text-gray-900">
                {formatAmount(payroll.sp_employee_total)} &euro;
              </span>
            </div>
          </div>

          {/* ZP employee */}
          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">ZP zamestnanec</h3>
            <AmountRow label="Vymeriavací základ" value={payroll.zp_assessment_base} />
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm font-semibold text-gray-800">ZP zamestnanec</span>
              <span className="text-sm font-bold text-gray-900">
                {formatAmount(payroll.zp_employee)} &euro;
              </span>
            </div>
          </div>

          {/* SP employer */}
          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
              SP zamestnávateľ
            </h3>
            <AmountRow label="Nemocenské" value={payroll.sp_employer_nemocenske} />
            <AmountRow label="Starobné" value={payroll.sp_employer_starobne} />
            <AmountRow label="Invalidné" value={payroll.sp_employer_invalidne} />
            <AmountRow label="Nezamestnanosť" value={payroll.sp_employer_nezamestnanost} />
            <AmountRow label="Garančné" value={payroll.sp_employer_garancne} />
            <AmountRow label="Rezervný fond" value={payroll.sp_employer_rezervny} />
            <AmountRow label="Kurzarbeit" value={payroll.sp_employer_kurzarbeit} />
            <AmountRow label="Úrazové" value={payroll.sp_employer_urazove} />
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm font-semibold text-gray-800">SP celkom</span>
              <span className="text-sm font-bold text-gray-900">
                {formatAmount(payroll.sp_employer_total)} &euro;
              </span>
            </div>
          </div>

          {/* ZP employer + extras */}
          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
              ZP zamestnávateľ &amp; Doplnkové
            </h3>
            <AmountRow label="ZP zamestnávateľ" value={payroll.zp_employer} />
            <AmountRow label="II. pilier" value={payroll.pillar2_amount} />
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm font-semibold text-gray-800">
                Náklady zamestnávateľa celkom
              </span>
              <span className="text-sm font-bold text-gray-900">
                {formatAmount(payroll.total_employer_cost)} &euro;
              </span>
            </div>
          </div>
        </div>

        {/* Metadata */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">Metadata</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Vypočítané:</span>{' '}
              <span className="text-gray-900">{formatDate(payroll.calculated_at)}</span>
            </div>
            <div>
              <span className="text-gray-500">Schválené:</span>{' '}
              <span className="text-gray-900">{formatDate(payroll.approved_at)}</span>
            </div>
            <div>
              <span className="text-gray-500">Schválil:</span>{' '}
              <span className="text-gray-900">{payroll.approved_by ?? '\u2014'}</span>
            </div>
            <div>
              <span className="text-gray-500">Vytvorené:</span>{' '}
              <span className="text-gray-900">{formatDate(payroll.created_at)}</span>
            </div>
            <div>
              <span className="text-gray-500">Aktualizované:</span>{' '}
              <span className="text-gray-900">{formatDate(payroll.updated_at)}</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // -- Render - Edit mode ----------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Úprava mzdy &mdash; {MONTH_NAMES[periodMonth]} {periodYear}
          </h1>
          <p className="mt-1 text-sm text-gray-600">{employeeName(payroll.employee_id)}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setEditMode(false)}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Zrušiť
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? 'Ukladám...' : 'Uložiť zmeny'}
          </button>
        </div>
      </div>

      {saveError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {saveError}
        </div>
      )}

      {/* Gross wage */}
      <fieldset className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <legend className="px-2 text-sm font-semibold text-gray-700">Hrubá mzda</legend>
        <div className="mt-2 grid grid-cols-3 gap-4">
          <NumberField
            label="Základná mzda"
            value={editForm.base_wage}
            onChange={(v) => updateEditField('base_wage', v)}
          />
          <NumberField
            label="Nadčasy (hodiny)"
            value={editForm.overtime_hours}
            onChange={(v) => updateEditField('overtime_hours', v)}
            step="0.5"
          />
          <NumberField
            label="Nadčasy (suma)"
            value={editForm.overtime_amount}
            onChange={(v) => updateEditField('overtime_amount', v)}
          />
          <NumberField
            label="Bonus"
            value={editForm.bonus_amount}
            onChange={(v) => updateEditField('bonus_amount', v)}
          />
          <NumberField
            label="Príplatky"
            value={editForm.supplement_amount}
            onChange={(v) => updateEditField('supplement_amount', v)}
          />
          <NumberField
            label="Hrubá mzda (vypočítané)"
            value={editForm.gross_wage}
            onChange={(v) => updateEditField('gross_wage', v)}
            disabled
          />
        </div>
      </fieldset>

      {/* SP employee (computed — read-only) */}
      <fieldset className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <legend className="px-2 text-sm font-semibold text-gray-700">SP zamestnanec (vypočítané)</legend>
        <div className="mt-2 grid grid-cols-3 gap-4">
          <NumberField label="Vymeriavací základ" value={editForm.sp_assessment_base} onChange={(v) => updateEditField('sp_assessment_base', v)} disabled />
          <NumberField label="Nemocenské" value={editForm.sp_nemocenske} onChange={(v) => updateEditField('sp_nemocenske', v)} disabled />
          <NumberField label="Starobné" value={editForm.sp_starobne} onChange={(v) => updateEditField('sp_starobne', v)} disabled />
          <NumberField label="Invalidné" value={editForm.sp_invalidne} onChange={(v) => updateEditField('sp_invalidne', v)} disabled />
          <NumberField label="Nezamestnanosť" value={editForm.sp_nezamestnanost} onChange={(v) => updateEditField('sp_nezamestnanost', v)} disabled />
          <NumberField label="SP celkom" value={editForm.sp_employee_total} onChange={(v) => updateEditField('sp_employee_total', v)} disabled />
        </div>
      </fieldset>

      {/* ZP employee (computed — read-only) */}
      <fieldset className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <legend className="px-2 text-sm font-semibold text-gray-700">ZP zamestnanec (vypočítané)</legend>
        <div className="mt-2 grid grid-cols-2 gap-4">
          <NumberField label="Vymeriavací základ" value={editForm.zp_assessment_base} onChange={(v) => updateEditField('zp_assessment_base', v)} disabled />
          <NumberField label="ZP zamestnanec" value={editForm.zp_employee} onChange={(v) => updateEditField('zp_employee', v)} disabled />
        </div>
      </fieldset>

      {/* Tax (computed — read-only) */}
      <fieldset className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <legend className="px-2 text-sm font-semibold text-gray-700">Daň (vypočítané)</legend>
        <div className="mt-2 grid grid-cols-3 gap-4">
          <NumberField label="Čiastkový základ dane" value={editForm.partial_tax_base} onChange={(v) => updateEditField('partial_tax_base', v)} disabled />
          <NumberField label="NCZD" value={editForm.nczd_applied} onChange={(v) => updateEditField('nczd_applied', v)} disabled />
          <NumberField label="Základ dane" value={editForm.tax_base} onChange={(v) => updateEditField('tax_base', v)} disabled />
          <NumberField label="Preddavok na daň" value={editForm.tax_advance} onChange={(v) => updateEditField('tax_advance', v)} disabled />
          <NumberField label="Detský bonus" value={editForm.child_bonus} onChange={(v) => updateEditField('child_bonus', v)} disabled />
          <NumberField label="Daň po bonuse" value={editForm.tax_after_bonus} onChange={(v) => updateEditField('tax_after_bonus', v)} disabled />
        </div>
      </fieldset>

      {/* Net wage (computed — read-only) */}
      <fieldset className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <legend className="px-2 text-sm font-semibold text-gray-700">Čistá mzda (vypočítané)</legend>
        <div className="mt-2">
          <NumberField label="Čistá mzda" value={editForm.net_wage} onChange={(v) => updateEditField('net_wage', v)} disabled />
        </div>
      </fieldset>

      {/* SP employer (computed — read-only) */}
      <fieldset className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <legend className="px-2 text-sm font-semibold text-gray-700">SP zamestnávateľ (vypočítané)</legend>
        <div className="mt-2 grid grid-cols-3 gap-4">
          <NumberField label="Nemocenské" value={editForm.sp_employer_nemocenske} onChange={(v) => updateEditField('sp_employer_nemocenske', v)} disabled />
          <NumberField label="Starobné" value={editForm.sp_employer_starobne} onChange={(v) => updateEditField('sp_employer_starobne', v)} disabled />
          <NumberField label="Invalidné" value={editForm.sp_employer_invalidne} onChange={(v) => updateEditField('sp_employer_invalidne', v)} disabled />
          <NumberField label="Nezamestnanosť" value={editForm.sp_employer_nezamestnanost} onChange={(v) => updateEditField('sp_employer_nezamestnanost', v)} disabled />
          <NumberField label="Garančné" value={editForm.sp_employer_garancne} onChange={(v) => updateEditField('sp_employer_garancne', v)} disabled />
          <NumberField label="Rezervný fond" value={editForm.sp_employer_rezervny} onChange={(v) => updateEditField('sp_employer_rezervny', v)} disabled />
          <NumberField label="Kurzarbeit" value={editForm.sp_employer_kurzarbeit} onChange={(v) => updateEditField('sp_employer_kurzarbeit', v)} disabled />
          <NumberField label="Úrazové" value={editForm.sp_employer_urazove} onChange={(v) => updateEditField('sp_employer_urazove', v)} disabled />
          <NumberField label="SP celkom" value={editForm.sp_employer_total} onChange={(v) => updateEditField('sp_employer_total', v)} disabled />
        </div>
      </fieldset>

      {/* ZP employer + extras (computed — read-only) */}
      <fieldset className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <legend className="px-2 text-sm font-semibold text-gray-700">
          ZP zamestnávateľ &amp; Doplnkové (vypočítané)
        </legend>
        <div className="mt-2 grid grid-cols-3 gap-4">
          <NumberField label="ZP zamestnávateľ" value={editForm.zp_employer} onChange={(v) => updateEditField('zp_employer', v)} disabled />
          <NumberField label="II. pilier" value={editForm.pillar2_amount} onChange={(v) => updateEditField('pillar2_amount', v)} disabled />
          <NumberField label="Náklady zamestnávateľa" value={editForm.total_employer_cost} onChange={(v) => updateEditField('total_employer_cost', v)} disabled />
        </div>
      </fieldset>

      {/* Save actions */}
      <div className="flex justify-end gap-3">
        <button
          onClick={() => setEditMode(false)}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Zrušiť
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {saving ? 'Ukladám...' : 'Uložiť zmeny'}
        </button>
      </div>
    </div>
  )
}

export default PayrollDetailPage
