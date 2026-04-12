import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock the service module
vi.mock('@/services/contribution-rate.service', () => ({
  listContributionRates: vi.fn(),
  getContributionRate: vi.fn(),
  createContributionRate: vi.fn(),
  updateContributionRate: vi.fn(),
  deleteContributionRate: vi.fn(),
}))

import ContributionRatesPage from '@/pages/ContributionRatesPage'
import {
  listContributionRates,
  createContributionRate,
  updateContributionRate,
  deleteContributionRate,
} from '@/services/contribution-rate.service'
import type { ContributionRateRead } from '@/types/contribution-rate'

const MOCK_RATE: ContributionRateRead = {
  id: '11111111-1111-1111-1111-111111111111',
  rate_type: 'sp_employee_nemocenske',
  rate_percent: '1.40',
  max_assessment_base: '8477.00',
  payer: 'employee',
  fund: 'nemocenske',
  valid_from: '2025-01-01',
  valid_to: null,
  created_at: '2025-01-01T00:00:00Z',
}

const MOCK_RATE_2: ContributionRateRead = {
  id: '22222222-2222-2222-2222-222222222222',
  rate_type: 'sp_employer_starobne',
  rate_percent: '14.00',
  max_assessment_base: '8477.00',
  payer: 'employer',
  fund: 'starobne',
  valid_from: '2025-01-01',
  valid_to: '2025-12-31',
  created_at: '2025-01-01T00:00:00Z',
}

function mockListResponse(items: ContributionRateRead[] = [MOCK_RATE, MOCK_RATE_2]) {
  vi.mocked(listContributionRates).mockResolvedValue({
    items,
    total: items.length,
    skip: 0,
    limit: 20,
  })
}

describe('ContributionRatesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListResponse()
  })

  it('renders page heading and data table', async () => {
    render(<ContributionRatesPage />)

    expect(screen.getByText('Sadzby odvodov')).toBeInTheDocument()
    expect(screen.getByText('+ Nová sadzba')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('sp_employee_nemocenske')).toBeInTheDocument()
    })

    expect(screen.getByText('sp_employer_starobne')).toBeInTheDocument()
    expect(screen.getByText('Zamestnanec')).toBeInTheDocument()
    expect(screen.getByText('Zamestnávateľ')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    // Make list hang so we can see loading state
    vi.mocked(listContributionRates).mockReturnValue(new Promise(() => {}))
    render(<ContributionRatesPage />)

    expect(screen.getByText('Načítavam...')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mockListResponse([])
    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('Žiadne sadzby odvodov')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    vi.mocked(listContributionRates).mockRejectedValue(new Error('Network error'))
    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('opens create modal on button click', async () => {
    const user = userEvent.setup()
    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('sp_employee_nemocenske')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nová sadzba'))

    expect(screen.getByText('Nová sadzba odvodu')).toBeInTheDocument()
    expect(screen.getByText('Vytvoriť')).toBeInTheDocument()
  })

  it('opens edit modal on Upraviť click', async () => {
    const user = userEvent.setup()
    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('sp_employee_nemocenske')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upraviť')
    await user.click(editButtons[0]!)

    expect(screen.getByText('Upraviť sadzbu')).toBeInTheDocument()
    expect(screen.getByText('Uložiť zmeny')).toBeInTheDocument()
  })

  it('submits create form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(createContributionRate).mockResolvedValue({
      ...MOCK_RATE,
      id: '33333333-3333-3333-3333-333333333333',
    })

    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('sp_employee_nemocenske')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nová sadzba'))

    // Fill form
    const rateTypeInput = screen.getByPlaceholderText('napr. standard')
    await user.type(rateTypeInput, 'sp_employee_starobne')

    const ratePercentInput = screen.getByPlaceholderText('napr. 4.00')
    await user.type(ratePercentInput, '4.00')

    // Find valid_from date input (first date input in the modal)
    const dateInputs = document.querySelectorAll<HTMLInputElement>('input[type="date"]')
    await user.type(dateInputs[0]!, '2025-01-01')

    await user.click(screen.getByText('Vytvoriť'))

    await waitFor(() => {
      expect(createContributionRate).toHaveBeenCalledTimes(1)
    })

    // List refreshed
    expect(listContributionRates).toHaveBeenCalledTimes(2) // initial + after create
  })

  it('submits edit form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(updateContributionRate).mockResolvedValue({
      ...MOCK_RATE,
      rate_percent: '1.40',
    })

    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('sp_employee_nemocenske')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upraviť')
    await user.click(editButtons[0]!)

    // The form should have pre-filled rate_type value
    const rateTypeInput = screen.getByDisplayValue('sp_employee_nemocenske')
    expect(rateTypeInput).toBeInTheDocument()

    // Submit with existing values
    await user.click(screen.getByText('Uložiť zmeny'))

    await waitFor(() => {
      expect(updateContributionRate).toHaveBeenCalledWith(
        MOCK_RATE.id,
        expect.objectContaining({
          rate_type: 'sp_employee_nemocenske',
          payer: 'employee',
          fund: 'nemocenske',
        }),
      )
    })
  })

  it('opens and confirms delete dialog', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteContributionRate).mockResolvedValue(undefined)

    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('sp_employee_nemocenske')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazať')
    await user.click(deleteButtons[0]!)

    // Confirm dialog
    expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()

    // Find the Zmazať button inside the confirmation dialog (not the table one)
    const confirmButton = screen.getAllByText('Zmazať').find(
      (btn) => btn.closest('.max-w-sm') !== null,
    )
    expect(confirmButton).toBeDefined()
    await user.click(confirmButton!)

    await waitFor(() => {
      expect(deleteContributionRate).toHaveBeenCalledWith(MOCK_RATE.id)
    })
  })

  it('cancels delete dialog', async () => {
    const user = userEvent.setup()

    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('sp_employee_nemocenske')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazať')
    await user.click(deleteButtons[0]!)

    expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()

    // Click Zrušiť
    const cancelButtons = screen.getAllByText('Zrušiť')
    await user.click(cancelButtons[cancelButtons.length - 1]!)

    expect(screen.queryByText('Potvrdiť zmazanie')).not.toBeInTheDocument()
    expect(deleteContributionRate).not.toHaveBeenCalled()
  })

  it('closes create modal on Zrušiť', async () => {
    const user = userEvent.setup()

    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('sp_employee_nemocenske')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nová sadzba'))
    expect(screen.getByText('Nová sadzba odvodu')).toBeInTheDocument()

    await user.click(screen.getByText('Zrušiť'))
    expect(screen.queryByText('Nová sadzba odvodu')).not.toBeInTheDocument()
  })

  it('shows form error on create failure', async () => {
    const user = userEvent.setup()
    vi.mocked(createContributionRate).mockRejectedValue(new Error('Duplicate rate'))

    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('sp_employee_nemocenske')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nová sadzba'))

    const rateTypeInput = screen.getByPlaceholderText('napr. standard')
    await user.type(rateTypeInput, 'test_type')

    const ratePercentInput = screen.getByPlaceholderText('napr. 4.00')
    await user.type(ratePercentInput, '1.00')

    const dateInputs2 = document.querySelectorAll<HTMLInputElement>('input[type="date"]')
    await user.type(dateInputs2[0]!, '2025-01-01')

    await user.click(screen.getByText('Vytvoriť'))

    await waitFor(() => {
      expect(screen.getByText('Duplicate rate')).toBeInTheDocument()
    })
  })

  it('displays fund labels correctly', async () => {
    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('Nemocenské poistenie')).toBeInTheDocument()
      expect(screen.getByText('Starobné poistenie')).toBeInTheDocument()
    })
  })

  it('formats percent and currency values', async () => {
    render(<ContributionRatesPage />)

    await waitFor(() => {
      expect(screen.getByText('1.40 %')).toBeInTheDocument()
      expect(screen.getByText('14.00 %')).toBeInTheDocument()
    })
  })
})
