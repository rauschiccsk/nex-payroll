import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock services before imports
const mockListPaySlips = vi.fn()
const mockDeletePaySlip = vi.fn()

vi.mock('@/services/pay-slip.service', () => ({
  listPaySlips: (...args: unknown[]) => mockListPaySlips(...args),
  getPaySlip: vi.fn(),
  createPaySlip: vi.fn(),
  updatePaySlip: vi.fn(),
  deletePaySlip: (...args: unknown[]) => mockDeletePaySlip(...args),
}))

import PaySlipsPage from '@/pages/PaySlipsPage'

const SAMPLE_PAY_SLIP = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-1',
  payroll_id: '22222222-2222-2222-2222-222222222222',
  employee_id: '33333333-3333-3333-3333-333333333333',
  period_year: 2026,
  period_month: 3,
  pdf_path: '/payslips/2026/03/E001.pdf',
  file_size_bytes: 45200,
  generated_at: '2026-03-15T10:00:00Z',
  downloaded_at: null,
}

const EMPTY_RESPONSE = { items: [], total: 0, skip: 0, limit: 50 }
const ONE_SLIP_RESPONSE = { items: [SAMPLE_PAY_SLIP], total: 1, skip: 0, limit: 50 }

describe('PaySlipsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page header', async () => {
    mockListPaySlips.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      render(<PaySlipsPage />)
    })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Výplatné pásky/)
  })

  it('renders pay slip records in the table after loading', async () => {
    mockListPaySlips.mockResolvedValue(ONE_SLIP_RESPONSE)

    await act(async () => {
      render(<PaySlipsPage />)
    })

    // Period should be displayed
    expect(await screen.findByText('03/2026')).toBeInTheDocument()
    // PDF filename
    expect(screen.getByText('E001.pdf')).toBeInTheDocument()
    // File size
    expect(screen.getByText('44.1 KB')).toBeInTheDocument()
    // Not downloaded badge
    expect(screen.getByText('Nestiahnuté')).toBeInTheDocument()
  })

  it('shows empty state when no records', async () => {
    mockListPaySlips.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      render(<PaySlipsPage />)
    })

    expect(await screen.findByText(/iadne záznamy/)).toBeInTheDocument()
  })

  it('opens create modal when button clicked', async () => {
    mockListPaySlips.mockResolvedValue(EMPTY_RESPONSE)
    const user = userEvent.setup()

    await act(async () => {
      render(<PaySlipsPage />)
    })

    const createBtn = await screen.findByRole('button', { name: /Nová výplatná/ })
    await user.click(createBtn)

    expect(await screen.findByRole('heading', { level: 2 })).toHaveTextContent(/Nová výplatná páska/)
  })

  it('closes create modal on cancel', async () => {
    mockListPaySlips.mockResolvedValue(EMPTY_RESPONSE)
    const user = userEvent.setup()

    await act(async () => {
      render(<PaySlipsPage />)
    })

    const createBtn = await screen.findByRole('button', { name: /Nová výplatná/ })
    await user.click(createBtn)

    // Modal open
    expect(screen.getByText('Nová výplatná páska')).toBeInTheDocument()

    // Click cancel
    const cancelBtn = screen.getByRole('button', { name: /Zrušiť/ })
    await user.click(cancelBtn)

    // Modal should be closed — heading gone
    await waitFor(() => {
      expect(screen.queryByText('Nová výplatná páska')).not.toBeInTheDocument()
    })
  })

  it('opens delete confirmation and deletes a pay slip', async () => {
    mockListPaySlips
      .mockResolvedValueOnce(ONE_SLIP_RESPONSE)
      .mockResolvedValueOnce(EMPTY_RESPONSE)
    mockDeletePaySlip.mockResolvedValue(undefined)
    const user = userEvent.setup()

    await act(async () => {
      render(<PaySlipsPage />)
    })

    // Wait for data
    expect(await screen.findByText('03/2026')).toBeInTheDocument()

    // Click table delete button
    const deleteButtons = screen.getAllByRole('button', { name: /Zmaz/ })
    await user.click(deleteButtons[0]!)

    // Confirm dialog appears
    expect(await screen.findByText(/Potvrdiť zmazanie/)).toBeInTheDocument()

    // Click confirm delete
    const allDeleteButtons = screen.getAllByRole('button', { name: /Zmaz/ })
    await user.click(allDeleteButtons[allDeleteButtons.length - 1]!)

    await waitFor(() => {
      expect(mockDeletePaySlip).toHaveBeenCalledWith(SAMPLE_PAY_SLIP.id)
    })
  })
})
