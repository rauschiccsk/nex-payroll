import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock services before imports
const mockListPaymentOrders = vi.fn()
const mockDeletePaymentOrder = vi.fn()
const mockListEmployees = vi.fn()
const mockListHealthInsurers = vi.fn()

vi.mock('@/services/payment-order.service', () => ({
  listPaymentOrders: (...args: unknown[]) => mockListPaymentOrders(...args),
  getPaymentOrder: vi.fn(),
  createPaymentOrder: vi.fn(),
  updatePaymentOrder: vi.fn(),
  deletePaymentOrder: (...args: unknown[]) => mockDeletePaymentOrder(...args),
}))

vi.mock('@/services/employee.service', () => ({
  listEmployees: (...args: unknown[]) => mockListEmployees(...args),
}))

vi.mock('@/services/health-insurer.service', () => ({
  listHealthInsurers: (...args: unknown[]) => mockListHealthInsurers(...args),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ tenantId: 'tenant-1' }),
  },
}))

import PaymentsPage from '@/pages/PaymentsPage'

const SAMPLE_ORDER = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-1',
  period_year: 2026,
  period_month: 4,
  payment_type: 'net_wage' as const,
  recipient_name: 'Jan Novak',
  recipient_iban: 'SK3112000000198742637541',
  recipient_bic: 'TATRSKBX',
  amount: '1843.04',
  variable_symbol: '0426',
  specific_symbol: null,
  constant_symbol: null,
  reference: null,
  status: 'pending' as const,
  employee_id: 'emp-1',
  health_insurer_id: null,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
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

const EMPTY_RESPONSE = { items: [], total: 0, skip: 0, limit: 20 }
const ONE_ORDER_RESPONSE = { items: [SAMPLE_ORDER], total: 1, skip: 0, limit: 20 }

describe('PaymentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListEmployees.mockResolvedValue({ items: [SAMPLE_EMPLOYEE], total: 1, skip: 0, limit: 1000 })
    mockListHealthInsurers.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 1000 })
  })

  it('renders the page header', async () => {
    mockListPaymentOrders.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      render(<PaymentsPage />)
    })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Platobné príkazy/)
  })

  it('renders payment order records in the table after loading', async () => {
    mockListPaymentOrders.mockResolvedValue(ONE_ORDER_RESPONSE)

    await act(async () => {
      render(<PaymentsPage />)
    })

    expect(await screen.findByText('Jan Novak')).toBeInTheDocument()
    expect(screen.getByText('Čistá mzda')).toBeInTheDocument()
    expect(screen.getByText('SK3112000000198742637541')).toBeInTheDocument()
  })

  it('shows empty state when no records', async () => {
    mockListPaymentOrders.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      render(<PaymentsPage />)
    })

    expect(await screen.findByText(/iadne z/)).toBeInTheDocument()
  })

  it('opens create modal when button clicked', async () => {
    mockListPaymentOrders.mockResolvedValue(EMPTY_RESPONSE)
    const user = userEvent.setup()

    await act(async () => {
      render(<PaymentsPage />)
    })

    const createBtn = await screen.findByRole('button', { name: /Nov/ })
    await user.click(createBtn)

    expect(await screen.findByRole('heading', { level: 2, name: /Nový platobný príkaz/ })).toBeInTheDocument()
  })

  it('opens delete confirmation and deletes a payment order', async () => {
    mockListPaymentOrders
      .mockResolvedValueOnce(ONE_ORDER_RESPONSE)
      .mockResolvedValueOnce(EMPTY_RESPONSE)
    mockDeletePaymentOrder.mockResolvedValue(undefined)
    const user = userEvent.setup()

    await act(async () => {
      render(<PaymentsPage />)
    })

    // Wait for data
    expect(await screen.findByText('Jan Novak')).toBeInTheDocument()

    // Click table delete button
    const deleteButtons = screen.getAllByRole('button', { name: /Zmaza/ })
    await user.click(deleteButtons[0]!)

    // Confirm dialog appears
    expect(await screen.findByText(/Potvrdi/)).toBeInTheDocument()

    // Click confirm delete
    const allDeleteButtons = screen.getAllByRole('button', { name: /Zmaza/ })
    await user.click(allDeleteButtons[allDeleteButtons.length - 1]!)

    await waitFor(() => {
      expect(mockDeletePaymentOrder).toHaveBeenCalledWith(SAMPLE_ORDER.id)
    })
  })
})
