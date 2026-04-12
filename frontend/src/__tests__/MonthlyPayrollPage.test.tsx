import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'

// Mock services before imports
const mockListPayrolls = vi.fn()
const mockCalculatePayroll = vi.fn()
const mockApprovePayroll = vi.fn()
const mockListEmployees = vi.fn()

vi.mock('@/services/payroll.service', () => ({
  listPayrolls: (...args: unknown[]) => mockListPayrolls(...args),
  calculatePayroll: (...args: unknown[]) => mockCalculatePayroll(...args),
  approvePayroll: (...args: unknown[]) => mockApprovePayroll(...args),
}))

vi.mock('@/services/employee.service', () => ({
  listEmployees: (...args: unknown[]) => mockListEmployees(...args),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ tenantId: 'tenant-1' }),
  },
}))

// Must import AFTER mocks
import MonthlyPayrollPage from '@/pages/MonthlyPayrollPage'

const SAMPLE_PAYROLL = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-1',
  employee_id: 'emp-1',
  contract_id: 'con-1',
  period_year: 2026,
  period_month: 3,
  status: 'draft' as const,
  base_wage: '2500.00',
  overtime_hours: '0.00',
  overtime_amount: '0.00',
  bonus_amount: '0.00',
  supplement_amount: '0.00',
  gross_wage: '2500.00',
  sp_assessment_base: '2500.00',
  sp_nemocenske: '35.00',
  sp_starobne: '100.00',
  sp_invalidne: '75.00',
  sp_nezamestnanost: '25.00',
  sp_employee_total: '235.00',
  zp_assessment_base: '2500.00',
  zp_employee: '100.00',
  partial_tax_base: '2165.00',
  nczd_applied: '470.47',
  tax_base: '1694.53',
  tax_advance: '321.96',
  child_bonus: '0.00',
  tax_after_bonus: '321.96',
  net_wage: '1843.04',
  sp_employer_nemocenske: '35.00',
  sp_employer_starobne: '350.00',
  sp_employer_invalidne: '75.00',
  sp_employer_nezamestnanost: '25.00',
  sp_employer_garancne: '6.25',
  sp_employer_rezervny: '118.75',
  sp_employer_kurzarbeit: '15.00',
  sp_employer_urazove: '20.00',
  sp_employer_total: '645.00',
  zp_employer: '250.00',
  total_employer_cost: '3395.00',
  pillar2_amount: '0.00',
  ai_validation_result: null,
  ledger_sync_status: null,
  calculated_at: null,
  approved_at: null,
  approved_by: null,
  created_at: '2026-03-01T00:00:00Z',
  updated_at: '2026-03-01T00:00:00Z',
}

const SAMPLE_EMPLOYEE = {
  id: 'emp-1',
  tenant_id: 'tenant-1',
  employee_number: 'E001',
  first_name: 'Jan',
  last_name: 'Novak',
  title_before: null,
  title_after: null,
  birth_date: '1990-01-01',
  birth_number: 'encrypted',
  gender: 'M' as const,
  nationality: 'SK',
  address_street: 'Hlavna 1',
  address_city: 'Bratislava',
  address_zip: '81101',
  address_country: 'SK',
  bank_iban: 'encrypted',
  bank_bic: null,
  health_insurer_id: 'hi-1',
  tax_declaration_type: 'standard' as const,
  nczd_applied: true,
  pillar2_saver: false,
  is_disabled: false,
  status: 'active' as const,
  hire_date: '2020-01-01',
  termination_date: null,
  is_deleted: false,
  created_at: '2020-01-01T00:00:00Z',
  updated_at: '2020-01-01T00:00:00Z',
}

const EMPTY_RESPONSE = { items: [], total: 0, skip: 0, limit: 50 }
const ONE_PAYROLL_RESPONSE = { items: [SAMPLE_PAYROLL], total: 1, skip: 0, limit: 50 }

function renderWithRouter(year = '2026', month = '3') {
  return render(
    <MemoryRouter initialEntries={[`/payroll/${year}/${month}`]}>
      <Routes>
        <Route path="/payroll/:year/:month" element={<MonthlyPayrollPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('MonthlyPayrollPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListEmployees.mockResolvedValue({
      items: [SAMPLE_EMPLOYEE],
      total: 1,
      skip: 0,
      limit: 1000,
    })
  })

  it('renders the page header', async () => {
    mockListPayrolls.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      renderWithRouter()
    })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Mzdy/)
  })

  it('displays payroll records in the table after loading', async () => {
    mockListPayrolls.mockResolvedValue(ONE_PAYROLL_RESPONSE)

    await act(async () => {
      renderWithRouter()
    })

    expect(await screen.findByText('Novak Jan')).toBeInTheDocument()
    // 'Koncept' appears in both filter dropdown and table badge — check at least one exists
    expect(screen.getAllByText('Koncept').length).toBeGreaterThanOrEqual(1)
  })

  it('shows empty state when no records', async () => {
    mockListPayrolls.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      renderWithRouter()
    })

    expect(await screen.findByText(/iadne z/)).toBeInTheDocument()
  })

  it('fetches employees with EMPLOYEE_FETCH_LIMIT', async () => {
    mockListPayrolls.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      renderWithRouter()
    })

    expect(mockListEmployees).toHaveBeenCalledWith({ skip: 0, limit: 1000 })
  })

  it('shows summary cards when records exist', async () => {
    mockListPayrolls.mockResolvedValue(ONE_PAYROLL_RESPONSE)

    await act(async () => {
      renderWithRouter()
    })

    await screen.findByText('Novak Jan')
    // Summary card labels
    expect(screen.getByText('Počet záznamov')).toBeInTheDocument()
    expect(screen.getByText('Hrubé mzdy')).toBeInTheDocument()
    expect(screen.getByText('Čisté mzdy')).toBeInTheDocument()
  })

  it('renders status filter dropdown', async () => {
    mockListPayrolls.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      renderWithRouter()
    })

    expect(screen.getByText('Status:')).toBeInTheDocument()
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('logs warning when employee fetch fails', async () => {
    mockListPayrolls.mockResolvedValue(EMPTY_RESPONSE)
    mockListEmployees.mockRejectedValue(new Error('network error'))
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    await act(async () => {
      renderWithRouter()
    })

    await waitFor(() => {
      expect(warnSpy).toHaveBeenCalledWith(
        'Failed to load employees for lookup:',
        expect.any(Error),
      )
    })
    warnSpy.mockRestore()
  })
})
