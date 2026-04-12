import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock the service module
vi.mock('@/services/tax-bracket.service', () => ({
  listTaxBrackets: vi.fn(),
  getTaxBracket: vi.fn(),
  createTaxBracket: vi.fn(),
  updateTaxBracket: vi.fn(),
  deleteTaxBracket: vi.fn(),
}))

import TaxBracketsPage from '@/pages/TaxBracketsPage'
import {
  listTaxBrackets,
  createTaxBracket,
  updateTaxBracket,
  deleteTaxBracket,
} from '@/services/tax-bracket.service'
import type { TaxBracketRead } from '@/types/tax-bracket'

const MOCK_BRACKET_1: TaxBracketRead = {
  id: '11111111-1111-1111-1111-111111111111',
  bracket_order: 1,
  min_amount: '0.00',
  max_amount: '47790.12',
  rate_percent: '19.00',
  nczd_annual: '5646.48',
  nczd_monthly: '470.54',
  nczd_reduction_threshold: '24952.06',
  nczd_reduction_formula: '44.2 * ZM - ZD',
  valid_from: '2025-01-01',
  valid_to: null,
  created_at: '2025-01-01T00:00:00Z',
}

const MOCK_BRACKET_2: TaxBracketRead = {
  id: '22222222-2222-2222-2222-222222222222',
  bracket_order: 2,
  min_amount: '47790.13',
  max_amount: null,
  rate_percent: '25.00',
  nczd_annual: '5646.48',
  nczd_monthly: '470.54',
  nczd_reduction_threshold: '24952.06',
  nczd_reduction_formula: '44.2 * ZM - ZD',
  valid_from: '2025-01-01',
  valid_to: '2025-12-31',
  created_at: '2025-01-01T00:00:00Z',
}

function mockListResponse(items: TaxBracketRead[] = [MOCK_BRACKET_1, MOCK_BRACKET_2]) {
  vi.mocked(listTaxBrackets).mockResolvedValue({
    items,
    total: items.length,
    skip: 0,
    limit: 20,
  })
}

describe('TaxBracketsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListResponse()
  })

  it('renders page heading and data table', async () => {
    render(<TaxBracketsPage />)

    expect(screen.getByText('Danove pasma')).toBeInTheDocument()
    expect(screen.getByText('+ Nove pasmo')).toBeInTheDocument()

    await waitFor(() => {
      // Slovak locale formats with comma: 19,00 %
      expect(screen.getByText('19,00 %')).toBeInTheDocument()
    })

    expect(screen.getByText('25,00 %')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    // Make list hang so we can see loading state
    vi.mocked(listTaxBrackets).mockReturnValue(new Promise(() => {}))
    render(<TaxBracketsPage />)

    expect(screen.getByText('Nacitavam...')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mockListResponse([])
    render(<TaxBracketsPage />)

    await waitFor(() => {
      expect(screen.getByText('Ziadne danove pasma')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    vi.mocked(listTaxBrackets).mockRejectedValue(new Error('Network error'))
    render(<TaxBracketsPage />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('opens create modal on button click', async () => {
    const user = userEvent.setup()
    render(<TaxBracketsPage />)

    await waitFor(() => {
      expect(screen.getByText('19,00 %')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nove pasmo'))

    expect(screen.getByText('Nove danove pasmo')).toBeInTheDocument()
    expect(screen.getByText('Vytvorit')).toBeInTheDocument()
  })

  it('opens edit modal on Upravit click', async () => {
    const user = userEvent.setup()
    render(<TaxBracketsPage />)

    await waitFor(() => {
      expect(screen.getByText('19,00 %')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upravit')
    await user.click(editButtons[0]!)

    expect(screen.getByText('Upravit danove pasmo')).toBeInTheDocument()
    expect(screen.getByText('Ulozit zmeny')).toBeInTheDocument()
  })

  it('submits create form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(createTaxBracket).mockResolvedValue({
      ...MOCK_BRACKET_1,
      id: '33333333-3333-3333-3333-333333333333',
    })

    render(<TaxBracketsPage />)

    await waitFor(() => {
      expect(screen.getByText('19,00 %')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nove pasmo'))

    // Fill required fields
    const orderInput = screen.getByPlaceholderText('napr. 1')
    await user.type(orderInput, '3')

    const rateInput = screen.getByPlaceholderText('napr. 19.00')
    await user.type(rateInput, '30.00')

    const minAmountInput = screen.getByPlaceholderText('napr. 0.00')
    await user.type(minAmountInput, '100000.00')

    const nczdAnnualInput = screen.getByPlaceholderText('napr. 5646.48')
    await user.type(nczdAnnualInput, '5646.48')

    const nczdMonthlyInput = screen.getByPlaceholderText('napr. 470.54')
    await user.type(nczdMonthlyInput, '470.54')

    const thresholdInput = screen.getByPlaceholderText('napr. 24952.06')
    await user.type(thresholdInput, '24952.06')

    const formulaInput = screen.getByPlaceholderText('napr. 44.2 * ZM - ZD')
    await user.type(formulaInput, '44.2 * ZM - ZD')

    // Find valid_from date input
    const dateInputs = document.querySelectorAll<HTMLInputElement>('input[type="date"]')
    await user.type(dateInputs[0]!, '2025-01-01')

    await user.click(screen.getByText('Vytvorit'))

    await waitFor(() => {
      expect(createTaxBracket).toHaveBeenCalledTimes(1)
    })

    // List refreshed
    expect(listTaxBrackets).toHaveBeenCalledTimes(2) // initial + after create
  })

  it('submits edit form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(updateTaxBracket).mockResolvedValue({
      ...MOCK_BRACKET_1,
      rate_percent: '20.00',
    })

    render(<TaxBracketsPage />)

    await waitFor(() => {
      expect(screen.getByText('19,00 %')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upravit')
    await user.click(editButtons[0]!)

    // The form should have pre-filled bracket_order value
    const orderInput = screen.getByDisplayValue('1')
    expect(orderInput).toBeInTheDocument()

    // Submit with existing values
    await user.click(screen.getByText('Ulozit zmeny'))

    await waitFor(() => {
      expect(updateTaxBracket).toHaveBeenCalledWith(
        MOCK_BRACKET_1.id,
        expect.objectContaining({
          bracket_order: 1,
          rate_percent: '19.00',
          nczd_reduction_formula: '44.2 * ZM - ZD',
        }),
      )
    })
  })

  it('opens and confirms delete dialog', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteTaxBracket).mockResolvedValue(undefined)

    render(<TaxBracketsPage />)

    await waitFor(() => {
      expect(screen.getByText('19,00 %')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazat')
    await user.click(deleteButtons[0]!)

    // Confirm dialog
    expect(screen.getByText('Potvrdit zmazanie')).toBeInTheDocument()

    // Find the Zmazat button inside the confirmation dialog
    const confirmButton = screen.getAllByText('Zmazat').find(
      (btn) => btn.closest('.max-w-sm') !== null,
    )
    expect(confirmButton).toBeDefined()
    await user.click(confirmButton!)

    await waitFor(() => {
      expect(deleteTaxBracket).toHaveBeenCalledWith(MOCK_BRACKET_1.id)
    })
  })

  it('cancels delete dialog', async () => {
    const user = userEvent.setup()

    render(<TaxBracketsPage />)

    await waitFor(() => {
      expect(screen.getByText('19,00 %')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazat')
    await user.click(deleteButtons[0]!)

    expect(screen.getByText('Potvrdit zmazanie')).toBeInTheDocument()

    // Click Zrusit
    const cancelButtons = screen.getAllByText('Zrusit')
    await user.click(cancelButtons[cancelButtons.length - 1]!)

    expect(screen.queryByText('Potvrdit zmazanie')).not.toBeInTheDocument()
    expect(deleteTaxBracket).not.toHaveBeenCalled()
  })

  it('closes create modal on Zrusit', async () => {
    const user = userEvent.setup()

    render(<TaxBracketsPage />)

    await waitFor(() => {
      expect(screen.getByText('19,00 %')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nove pasmo'))
    expect(screen.getByText('Nove danove pasmo')).toBeInTheDocument()

    await user.click(screen.getByText('Zrusit'))
    expect(screen.queryByText('Nove danove pasmo')).not.toBeInTheDocument()
  })

  it('shows form error on create failure', async () => {
    const user = userEvent.setup()
    vi.mocked(createTaxBracket).mockRejectedValue(new Error('Duplicate bracket'))

    render(<TaxBracketsPage />)

    await waitFor(() => {
      expect(screen.getByText('19,00 %')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nove pasmo'))

    // Fill required fields
    const orderInput = screen.getByPlaceholderText('napr. 1')
    await user.type(orderInput, '1')

    const rateInput = screen.getByPlaceholderText('napr. 19.00')
    await user.type(rateInput, '19.00')

    const minAmountInput = screen.getByPlaceholderText('napr. 0.00')
    await user.type(minAmountInput, '0.00')

    const nczdAnnualInput = screen.getByPlaceholderText('napr. 5646.48')
    await user.type(nczdAnnualInput, '5646.48')

    const nczdMonthlyInput = screen.getByPlaceholderText('napr. 470.54')
    await user.type(nczdMonthlyInput, '470.54')

    const thresholdInput = screen.getByPlaceholderText('napr. 24952.06')
    await user.type(thresholdInput, '24952.06')

    const formulaInput = screen.getByPlaceholderText('napr. 44.2 * ZM - ZD')
    await user.type(formulaInput, 'test formula')

    const dateInputs = document.querySelectorAll<HTMLInputElement>('input[type="date"]')
    await user.type(dateInputs[0]!, '2025-01-01')

    await user.click(screen.getByText('Vytvorit'))

    await waitFor(() => {
      expect(screen.getByText('Duplicate bracket')).toBeInTheDocument()
    })
  })

  it('formats currency values with euro sign', async () => {
    render(<TaxBracketsPage />)

    await waitFor(() => {
      // Check that currency formatting works (locale-dependent but should have euro sign)
      const cells = document.querySelectorAll('td')
      const cellTexts = Array.from(cells).map((c) => c.textContent)
      // Should contain formatted amounts
      expect(cellTexts.some((t) => t?.includes('\u20AC'))).toBe(true)
    })
  })

  it('displays dash for null max_amount', async () => {
    render(<TaxBracketsPage />)

    await waitFor(() => {
      // MOCK_BRACKET_2 has null max_amount — should show dash
      const cells = document.querySelectorAll('td')
      const cellTexts = Array.from(cells).map((c) => c.textContent)
      expect(cellTexts.some((t) => t === '\u2014')).toBe(true)
    })
  })
})
