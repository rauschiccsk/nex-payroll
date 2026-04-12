import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import type { PayrollRead, PayrollStatus, LedgerSyncStatus } from '@/types/payroll'
import { listPayrolls, calculatePayroll, approvePayroll } from '@/services/payroll.service'
import { listEmployees } from '@/services/employee.service'
import type { EmployeeRead } from '@/types/employee'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 50
const EMPLOYEE_FETCH_LIMIT = 1000

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

// -- Helpers -----------------------------------------------------------------
function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

function formatAmount(amount: string): string {
  const n = parseFloat(amount) || 0
  return n.toLocaleString('sk-SK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// -- Component ---------------------------------------------------------------
function MonthlyPayrollPage() {
  const { year, month } = useParams<{ year: string; month: string }>()
  const navigate = useNavigate()
  const periodYear = Number(year)
  const periodMonth = Number(month)

  // List state
  const [items, setItems] = useState<PayrollRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail modal state
  const [detail, setDetail] = useState<PayrollRead | null>(null)

  // Action state
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Status filter
  const [statusFilter, setStatusFilter] = useState<PayrollStatus | ''>('')

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

  function employeeName(id: string): string {
    const emp = employeeMap[id]
    return emp ? `${emp.last_name} ${emp.first_name}` : id.substring(0, 8) + '...'
  }

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, unknown> = {
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
        period_year: periodYear,
        period_month: periodMonth,
      }
      if (statusFilter) {
        params.status = statusFilter
      }
      const res = await listPayrolls(params as Parameters<typeof listPayrolls>[0])
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nepodarilo sa načítať dáta')
    } finally {
      setLoading(false)
    }
  }, [page, periodYear, periodMonth, statusFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // -- Actions ---------------------------------------------------------------
  async function handleCalculate(item: PayrollRead) {
    setActionLoading(item.id)
    try {
      await calculatePayroll(item.id)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri výpočte')
    } finally {
      setActionLoading(null)
    }
  }

  async function handleApprove(item: PayrollRead) {
    setActionLoading(item.id)
    try {
      await approvePayroll(item.id)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri schvaľovaní')
    } finally {
      setActionLoading(null)
    }
  }

  // -- Summary ---------------------------------------------------------------
  const summaryGross = items.reduce((s, i) => s + (parseFloat(i.gross_wage) || 0), 0)
  const summaryNet = items.reduce((s, i) => s + (parseFloat(i.net_wage) || 0), 0)
  const summaryEmployerCost = items.reduce(
    (s, i) => s + (parseFloat(i.total_employer_cost) || 0),
    0,
  )

  // -- Render ----------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Mzdy &mdash; {MONTH_NAMES[periodMonth]} {periodYear}
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Mzdové výpočty za obdobie {String(periodMonth).padStart(2, '0')}/{periodYear}
          </p>
        </div>
        <button
          onClick={() => navigate('/payroll')}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          &larr; Späť na prehľad
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-sm text-gray-700">
          Status:
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as PayrollStatus | '')
              setPage(0)
            }}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
          >
            <option value="">Všetky</option>
            {(Object.keys(STATUS_LABELS) as PayrollStatus[]).map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Summary cards */}
      {items.length > 0 && (
        <div className="grid grid-cols-4 gap-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-sm text-gray-500">Počet záznamov</p>
            <p className="text-xl font-bold text-gray-900">{total}</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-sm text-gray-500">Hrubé mzdy</p>
            <p className="text-xl font-bold text-gray-900">
              {summaryGross.toLocaleString('sk-SK', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{' '}
              &euro;
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-sm text-gray-500">Čisté mzdy</p>
            <p className="text-xl font-bold text-primary-700">
              {summaryNet.toLocaleString('sk-SK', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{' '}
              &euro;
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-sm text-gray-500">Náklady zamestnávateľa</p>
            <p className="text-xl font-bold text-gray-900">
              {summaryEmployerCost.toLocaleString('sk-SK', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{' '}
              &euro;
            </p>
          </div>
        </div>
      )}

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
                Detail mzdy &mdash; {employeeName(detail.employee_id)}
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
                {employeeName(detail.employee_id)}
              </div>
              <div>
                <span className="font-medium text-gray-500">Zmluva ID:</span>{' '}
                {detail.contract_id.substring(0, 8)}...
              </div>
              <div>
                <span className="font-medium text-gray-500">Obdobie:</span>{' '}
                {String(detail.period_month).padStart(2, '0')}/{detail.period_year}
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

            <h3 className="mt-4 text-sm font-semibold text-gray-700">Daň</h3>
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
                Zamestnanec
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Status
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Hrubá mzda
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                SP zam.
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                ZP zam.
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Daň
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Čistá mzda
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Náklady zam.
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
                  Načítavam...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-sm text-gray-500">
                  Žiadne záznamy za toto obdobie
                </td>
              </tr>
            )}
            {!loading &&
              items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="max-w-[180px] truncate whitespace-nowrap px-4 py-3 text-sm text-gray-900">
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
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-600">
                    {formatAmount(item.sp_employee_total)} &euro;
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-600">
                    {formatAmount(item.zp_employee)} &euro;
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-600">
                    {formatAmount(item.tax_after_bonus)} &euro;
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-medium text-primary-700">
                    {formatAmount(item.net_wage)} &euro;
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-600">
                    {formatAmount(item.total_employer_cost)} &euro;
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
                      onClick={() =>
                        navigate(`/payroll/${item.period_year}/${item.period_month}/${item.id}`)
                      }
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Otvoriť
                    </button>
                    {item.status === 'draft' && (
                      <button
                        onClick={() => handleCalculate(item)}
                        disabled={actionLoading === item.id}
                        className="mr-2 text-blue-600 hover:text-blue-800 disabled:opacity-50"
                      >
                        {actionLoading === item.id ? '...' : 'Vypočítať'}
                      </button>
                    )}
                    {item.status === 'calculated' && (
                      <button
                        onClick={() => handleApprove(item)}
                        disabled={actionLoading === item.id}
                        className="text-green-600 hover:text-green-800 disabled:opacity-50"
                      >
                        {actionLoading === item.id ? '...' : 'Schváliť'}
                      </button>
                    )}
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
    </div>
  )
}

export default MonthlyPayrollPage
