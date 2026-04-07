// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom/vitest'

// Mock services before imports
const mockListPayrolls = vi.fn()
const mockDeletePayroll = vi.fn()
const mockListEmployees = vi.fn()

vi.mock('@/services/payroll.service', () => ({
  listPayrolls: (...args: unknown[]) => mockListPayrolls(...args),
  getPayroll: vi.fn(),
  createPayroll: vi.fn(),
  updatePayroll: vi.fn(),
  deletePayroll: (...args: unknown[]) => mockDeletePayroll(...args),
}))

vi.mock('@/services/employee.service', () => ({
  listEmployees: (...args: unknown[]) => mockListEmployees(...args),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ tenantId: 'tenant-1' }),
  },
}))

import PayrollPage from '@/pages/PayrollPage'

const SAMPLE_PAYROLL = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-1',
  employee_id: 'emp-1',
  contract_id: 'con-1',
  period_year: 2026,
  period_month: 3,
  status: 'draft' as const,
  base_wage: 2500.0,
  overtime_hours: 0,
  overtime_amount: 0,
  bonus_amount: 0,
  supplement_amount: 0,
  gross_wage: 2500.0,
  sp_assessment_base: 2500.0,
  sp_nemocenske: 35.0,
  sp_starobne: 100.0,
  sp_invalidne: 75.0,
  sp_nezamestnanost: 25.0,
  sp_employee_total: 235.0,
  zp_assessment_base: 2500.0,
  zp_employee: 100.0,
  partial_tax_base: 2165.0,
  nczd_applied: 470.47,
  tax_base: 1694.53,
  tax_advance: 321.96,
  child_bonus: 0,
  tax_after_bonus: 321.96,
  net_wage: 1843.04,
  sp_employer_nemocenske: 35.0,
  sp_employer_starobne: 350.0,
  sp_employer_invalidne: 75.0,
  sp_employer_nezamestnanost: 25.0,
  sp_employer_garancne: 6.25,
  sp_employer_rezervny: 118.75,
  sp_employer_kurzarbeit: 15.0,
  sp_employer_urazove: 20.0,
  sp_employer_total: 645.0,
  zp_employer: 250.0,
  total_employer_cost: 3395.0,
  pillar2_amount: 0,
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

describe('PayrollPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListEmployees.mockResolvedValue({ items: [SAMPLE_EMPLOYEE], total: 1, skip: 0, limit: 1000 })
  })

  it('renders the page header', async () => {
    mockListPayrolls.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      render(<PayrollPage />)
    })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Mzdy/)
  })

  it('renders payroll records in the table after loading', async () => {
    mockListPayrolls.mockResolvedValue(ONE_PAYROLL_RESPONSE)

    await act(async () => {
      render(<PayrollPage />)
    })

    // Wait for async data — employee name should be resolved
    expect(await screen.findByText('Novak Jan')).toBeInTheDocument()
    expect(screen.getByText('Koncept')).toBeInTheDocument()
  })

  it('shows empty state when no records', async () => {
    mockListPayrolls.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      render(<PayrollPage />)
    })

    expect(await screen.findByText(/iadne z/)).toBeInTheDocument()
  })

  it('opens create modal when button clicked', async () => {
    mockListPayrolls.mockResolvedValue(EMPTY_RESPONSE)
    const user = userEvent.setup()

    await act(async () => {
      render(<PayrollPage />)
    })

    const createBtn = await screen.findByRole('button', { name: /Nov/ })
    await user.click(createBtn)

    expect(await screen.findByRole('heading', { level: 2 })).toHaveTextContent(/Nov.*mzda/)
  })

  it('opens delete confirmation and deletes a payroll', async () => {
    mockListPayrolls
      .mockResolvedValueOnce(ONE_PAYROLL_RESPONSE)
      .mockResolvedValueOnce(EMPTY_RESPONSE)
    mockDeletePayroll.mockResolvedValue(undefined)
    const user = userEvent.setup()

    await act(async () => {
      render(<PayrollPage />)
    })

    // Wait for data
    expect(await screen.findByText('Novak Jan')).toBeInTheDocument()

    // Click table delete button
    const deleteButtons = screen.getAllByRole('button', { name: /Zmaz/ })
    await user.click(deleteButtons[0]!)

    // Confirm dialog appears
    expect(await screen.findByText(/Potvrdenie/)).toBeInTheDocument()

    // Click confirm delete — last Zmazať button is the confirm one
    const allDeleteButtons = screen.getAllByRole('button', { name: /Zmaz/ })
    await user.click(allDeleteButtons[allDeleteButtons.length - 1]!)

    await waitFor(() => {
      expect(mockDeletePayroll).toHaveBeenCalledWith(SAMPLE_PAYROLL.id)
    })
  })
})
