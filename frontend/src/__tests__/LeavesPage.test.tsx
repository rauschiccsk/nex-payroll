// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom/vitest'

// Mock services before imports
const mockListLeaves = vi.fn()
const mockDeleteLeave = vi.fn()
const mockListEmployees = vi.fn()

vi.mock('@/services/leave.service', () => ({
  listLeaves: (...args: unknown[]) => mockListLeaves(...args),
  getLeave: vi.fn(),
  createLeave: vi.fn(),
  updateLeave: vi.fn(),
  deleteLeave: (...args: unknown[]) => mockDeleteLeave(...args),
}))

vi.mock('@/services/employee.service', () => ({
  listEmployees: (...args: unknown[]) => mockListEmployees(...args),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ tenantId: 'tenant-1' }),
  },
}))

import LeavesPage from '@/pages/LeavesPage'

const SAMPLE_LEAVE = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-1',
  employee_id: 'emp-1',
  leave_type: 'annual' as const,
  start_date: '2026-04-01',
  end_date: '2026-04-10',
  business_days: 8,
  status: 'pending' as const,
  note: null,
  approved_by: null,
  approved_at: null,
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
const ONE_LEAVE_RESPONSE = { items: [SAMPLE_LEAVE], total: 1, skip: 0, limit: 20 }

describe('LeavesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListEmployees.mockResolvedValue({ items: [SAMPLE_EMPLOYEE], total: 1, skip: 0, limit: 1000 })
  })

  it('renders the page header', async () => {
    mockListLeaves.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      render(<LeavesPage />)
    })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Dovolenky/)
  })

  it('renders leave records in the table after loading', async () => {
    mockListLeaves.mockResolvedValue(ONE_LEAVE_RESPONSE)

    await act(async () => {
      render(<LeavesPage />)
    })

    // Wait for async data to render
    expect(await screen.findByText('Novak Jan')).toBeInTheDocument()
    expect(screen.getByText('Dovolenka')).toBeInTheDocument()
  })

  it('shows empty state when no records', async () => {
    mockListLeaves.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      render(<LeavesPage />)
    })

    expect(await screen.findByText(/iadne z/)).toBeInTheDocument()
  })

  it('opens create modal when button clicked', async () => {
    mockListLeaves.mockResolvedValue(EMPTY_RESPONSE)
    const user = userEvent.setup()

    await act(async () => {
      render(<LeavesPage />)
    })

    const createBtn = await screen.findByRole('button', { name: /Nov/ })
    await user.click(createBtn)

    expect(await screen.findByText(/iadosť o nepr/i)).toBeInTheDocument()
  })

  it('opens delete confirmation and deletes a leave', async () => {
    mockListLeaves
      .mockResolvedValueOnce(ONE_LEAVE_RESPONSE)
      .mockResolvedValueOnce(EMPTY_RESPONSE)
    mockDeleteLeave.mockResolvedValue(undefined)
    const user = userEvent.setup()

    await act(async () => {
      render(<LeavesPage />)
    })

    // Wait for data
    expect(await screen.findByText('Novak Jan')).toBeInTheDocument()

    // Click table delete button
    const deleteButtons = screen.getAllByRole('button', { name: /Zmaza/ })
    await user.click(deleteButtons[0]!)

    // Confirm dialog appears
    expect(await screen.findByText(/Potvrdi/)).toBeInTheDocument()

    // Click confirm delete
    const allDeleteButtons = screen.getAllByRole('button', { name: /Zmaza/ })
    await user.click(allDeleteButtons[allDeleteButtons.length - 1]!)

    await waitFor(() => {
      expect(mockDeleteLeave).toHaveBeenCalledWith(SAMPLE_LEAVE.id)
    })
  })
})
