import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock react-router
const mockNavigate = vi.fn()
vi.mock('react-router', () => ({
  useNavigate: () => mockNavigate,
}))

// Mock services
const mockCreateEmployee = vi.fn()
const mockListHealthInsurers = vi.fn()

vi.mock('@/services/employee.service', () => ({
  createEmployee: (...args: unknown[]) => mockCreateEmployee(...args),
  listEmployees: vi.fn(),
  getEmployee: vi.fn(),
  updateEmployee: vi.fn(),
  deleteEmployee: vi.fn(),
}))

vi.mock('@/services/health-insurer.service', () => ({
  listHealthInsurers: (...args: unknown[]) => mockListHealthInsurers(...args),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ token: 'test-token', tenantId: 'tenant-123' }),
  },
}))

import EmployeeFormPage from '@/pages/EmployeeFormPage'

const SAMPLE_INSURER = {
  id: 'hi-1',
  code: '25',
  name: 'VšZP',
  iban: 'SK0000000000000000000000',
  bic: null,
  is_active: true,
  created_at: '2025-01-01T00:00:00Z',
}

describe('EmployeeFormPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListHealthInsurers.mockResolvedValue({
      items: [SAMPLE_INSURER],
      total: 1,
      skip: 0,
      limit: 100,
    })
  })

  it('renders the create form with page heading', async () => {
    await act(async () => {
      render(<EmployeeFormPage />)
    })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Nový zamestnanec')
    expect(screen.getByText('Vytvorenie nového zamestnanca')).toBeInTheDocument()
  })

  it('displays correct diacritics in labels', async () => {
    await act(async () => {
      render(<EmployeeFormPage />)
    })

    // Step 1 heading (use getAllByText since step indicator also has same text)
    const osobneElements = screen.getAllByText('Osobné údaje')
    expect(osobneElements.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Číslo zamestnanca')).toBeInTheDocument()
    expect(screen.getByText('Dátum narodenia')).toBeInTheDocument()
    expect(screen.getByText(/Rodné číslo/)).toBeInTheDocument()
    expect(screen.getByText('Národnosť')).toBeInTheDocument()
  })

  it('does not expose tenant_id as a form field', async () => {
    await act(async () => {
      render(<EmployeeFormPage />)
    })

    // tenant_id should NOT be visible to user
    expect(screen.queryByText('Tenant ID')).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText('UUID organizacie')).not.toBeInTheDocument()
  })

  it('shows step navigation and can navigate between steps', async () => {
    const user = userEvent.setup()

    await act(async () => {
      render(<EmployeeFormPage />)
    })

    // Initial step shows personal info heading
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Osobné údaje')

    // Click Ďalej to go to address step
    await user.click(screen.getByRole('button', { name: /Ďalej/ }))
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Adresa')

    // Click Späť to go back (exact match to avoid matching "Späť na zoznam")
    await user.click(screen.getByRole('button', { name: /^Späť$/ }))
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Osobné údaje')
  })

  it('navigates back on Zrušiť click', async () => {
    const user = userEvent.setup()

    await act(async () => {
      render(<EmployeeFormPage />)
    })

    await user.click(screen.getByRole('button', { name: /Zrušiť/ }))

    expect(mockNavigate).toHaveBeenCalledWith('/employees')
  })

  it('submits form with tenant_id from auth store', async () => {
    const user = userEvent.setup()
    mockCreateEmployee.mockResolvedValue({
      id: 'new-emp-id',
      tenant_id: 'tenant-123',
      employee_number: 'E001',
      first_name: 'Ján',
      last_name: 'Novák',
    })

    await act(async () => {
      render(<EmployeeFormPage />)
    })

    // Fill step 1 - personal
    await user.type(screen.getByPlaceholderText('napr. EMP001'), 'E001')
    await user.type(screen.getByPlaceholderText('napr. Ján'), 'Ján')
    await user.type(screen.getByPlaceholderText('napr. Novák'), 'Novák')
    // Use direct DOM query for date inputs (no htmlFor)
    const dateInputs = document.querySelectorAll<HTMLInputElement>('input[type="date"]')
    if (dateInputs[0]) {
      await user.clear(dateInputs[0])
      await user.type(dateInputs[0], '1990-01-15')
    }
    await user.type(screen.getByPlaceholderText('napr. 900101/1234'), '900115/1234')

    // Navigate to step 2 (address)
    await user.click(screen.getByRole('button', { name: /Ďalej/ }))

    // Fill address
    await user.type(screen.getByPlaceholderText('napr. Hlavná 1'), 'Hlavná 1')
    await user.type(screen.getByPlaceholderText('napr. Bratislava'), 'Bratislava')
    await user.type(screen.getByPlaceholderText('napr. 81101'), '81101')

    // Navigate to step 3 (bank)
    await user.click(screen.getByRole('button', { name: /Ďalej/ }))

    // Fill bank
    await user.type(screen.getByPlaceholderText('SK...'), 'SK3112000000198742637541')

    // Navigate to step 4 (employment)
    await user.click(screen.getByRole('button', { name: /Ďalej/ }))

    // Fill hire date
    const hireDateInputs = document.querySelectorAll<HTMLInputElement>('input[type="date"]')
    if (hireDateInputs[0]) {
      await user.clear(hireDateInputs[0])
      await user.type(hireDateInputs[0], '2020-01-01')
    }

    // Wait for insurers to load and select one
    await waitFor(() => {
      expect(screen.getByText('25 - VšZP')).toBeInTheDocument()
    })
    const insurerSelect = document.querySelector<HTMLSelectElement>('select[required]')
    if (insurerSelect) {
      await user.selectOptions(insurerSelect, 'hi-1')
    }

    // Submit
    await user.click(screen.getByRole('button', { name: /Vytvoriť zamestnanca/ }))

    await waitFor(() => {
      expect(mockCreateEmployee).toHaveBeenCalledWith(
        expect.objectContaining({
          tenant_id: 'tenant-123',
          employee_number: 'E001',
          first_name: 'Ján',
          last_name: 'Novák',
        }),
      )
    })

    expect(mockNavigate).toHaveBeenCalledWith('/employees/new-emp-id')
  })

  it('shows error message on submit failure', async () => {
    const user = userEvent.setup()
    mockCreateEmployee.mockRejectedValue(new Error('Duplicate employee number'))

    await act(async () => {
      render(<EmployeeFormPage />)
    })

    // Fill required fields on step 1
    await user.type(screen.getByPlaceholderText('napr. EMP001'), 'E001')
    await user.type(screen.getByPlaceholderText('napr. Ján'), 'Ján')
    await user.type(screen.getByPlaceholderText('napr. Novák'), 'Novák')
    const birthDates = document.querySelectorAll<HTMLInputElement>('input[type="date"]')
    if (birthDates[0]) {
      await user.clear(birthDates[0])
      await user.type(birthDates[0], '1990-01-15')
    }
    await user.type(screen.getByPlaceholderText('napr. 900101/1234'), '900115/1234')

    // Navigate to step 2
    await user.click(screen.getByRole('button', { name: /Ďalej/ }))
    await user.type(screen.getByPlaceholderText('napr. Hlavná 1'), 'Test 1')
    await user.type(screen.getByPlaceholderText('napr. Bratislava'), 'Test')
    await user.type(screen.getByPlaceholderText('napr. 81101'), '00000')

    // Navigate to step 3
    await user.click(screen.getByRole('button', { name: /Ďalej/ }))
    await user.type(screen.getByPlaceholderText('SK...'), 'SK3112000000198742637541')

    // Navigate to step 4
    await user.click(screen.getByRole('button', { name: /Ďalej/ }))
    const hireDates = document.querySelectorAll<HTMLInputElement>('input[type="date"]')
    if (hireDates[0]) {
      await user.clear(hireDates[0])
      await user.type(hireDates[0], '2020-01-01')
    }

    // Select insurer
    await waitFor(() => {
      expect(screen.getByText('25 - VšZP')).toBeInTheDocument()
    })
    const insurerSel = document.querySelector<HTMLSelectElement>('select[required]')
    if (insurerSel) {
      await user.selectOptions(insurerSel, 'hi-1')
    }

    // Submit
    await user.click(screen.getByRole('button', { name: /Vytvoriť zamestnanca/ }))

    await waitFor(() => {
      expect(screen.getByText('Duplicate employee number')).toBeInTheDocument()
    })
  })
})
