import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock react-router
const mockNavigate = vi.fn()
vi.mock('react-router', () => ({
  useParams: () => ({ id: '11111111-1111-1111-1111-111111111111' }),
  useNavigate: () => mockNavigate,
}))

// Mock services
const mockGetEmployee = vi.fn()
const mockUpdateEmployee = vi.fn()
const mockDeleteEmployee = vi.fn()
const mockListHealthInsurers = vi.fn()

vi.mock('@/services/employee.service', () => ({
  getEmployee: (...args: unknown[]) => mockGetEmployee(...args),
  updateEmployee: (...args: unknown[]) => mockUpdateEmployee(...args),
  deleteEmployee: (...args: unknown[]) => mockDeleteEmployee(...args),
  listEmployees: vi.fn(),
  createEmployee: vi.fn(),
}))

vi.mock('@/services/health-insurer.service', () => ({
  listHealthInsurers: (...args: unknown[]) => mockListHealthInsurers(...args),
}))

import EmployeeDetailPage from '@/pages/EmployeeDetailPage'
import type { EmployeeRead } from '@/types/employee'

const SAMPLE_EMPLOYEE: EmployeeRead = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-1',
  employee_number: 'E001',
  first_name: 'Ján',
  last_name: 'Novák',
  title_before: 'Ing.',
  title_after: null,
  birth_date: '1990-01-15',
  birth_number: '900115/1234',
  gender: 'M',
  nationality: 'SK',
  address_street: 'Hlavná 1',
  address_city: 'Bratislava',
  address_zip: '81101',
  address_country: 'SK',
  bank_iban: 'SK3112000000198742637541',
  bank_bic: 'SUBASKBX',
  health_insurer_id: 'hi-1',
  tax_declaration_type: 'standard',
  nczd_applied: true,
  pillar2_saver: false,
  is_disabled: false,
  status: 'active',
  hire_date: '2020-01-01',
  termination_date: null,
  is_deleted: false,
  created_at: '2020-01-01T00:00:00Z',
  updated_at: '2020-01-01T00:00:00Z',
}

const SAMPLE_INSURER = {
  id: 'hi-1',
  code: '25',
  name: 'VšZP',
  iban: 'SK0000000000000000000000',
  bic: null,
  is_active: true,
  created_at: '2025-01-01T00:00:00Z',
}

describe('EmployeeDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListHealthInsurers.mockResolvedValue({
      items: [SAMPLE_INSURER],
      total: 1,
      skip: 0,
      limit: 100,
    })
  })

  it('renders employee details after loading', async () => {
    mockGetEmployee.mockResolvedValue(SAMPLE_EMPLOYEE)

    render(<EmployeeDetailPage />)

    // Wait for data to render
    expect(await screen.findByText(/Ing\. Ján Novák/)).toBeInTheDocument()
    expect(screen.getByText('E001')).toBeInTheDocument()
    expect(screen.getByText('Aktívny')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    mockGetEmployee.mockReturnValue(new Promise(() => {}))

    render(<EmployeeDetailPage />)

    expect(screen.getByText('Načítavam...')).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    mockGetEmployee.mockRejectedValue(new Error('Network error'))

    render(<EmployeeDetailPage />)

    expect(await screen.findByText('Network error')).toBeInTheDocument()
  })

  it('displays correct diacritics in labels', async () => {
    mockGetEmployee.mockResolvedValue(SAMPLE_EMPLOYEE)

    render(<EmployeeDetailPage />)

    await screen.findByText(/Ing\. Ján Novák/)

    // Verify diacritics in section headers
    expect(screen.getByText('Osobné údaje')).toBeInTheDocument()
    expect(screen.getByText('Bankové údaje')).toBeInTheDocument()
    expect(screen.getByText('Pracovné údaje')).toBeInTheDocument()
    expect(screen.getByText('Príznaky')).toBeInTheDocument()
  })

  it('opens edit modal on Upraviť click', async () => {
    mockGetEmployee.mockResolvedValue(SAMPLE_EMPLOYEE)
    const user = userEvent.setup()

    render(<EmployeeDetailPage />)

    await screen.findByText(/Ing\. Ján Novák/)

    await user.click(screen.getByRole('button', { name: /Upraviť/ }))

    expect(screen.getByText('Upraviť zamestnanca')).toBeInTheDocument()
    expect(screen.getByDisplayValue('E001')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Ján')).toBeInTheDocument()
  })

  it('submits edit form and updates employee', async () => {
    const updatedEmployee = { ...SAMPLE_EMPLOYEE, first_name: 'Peter' }
    mockGetEmployee.mockResolvedValue(SAMPLE_EMPLOYEE)
    mockUpdateEmployee.mockResolvedValue(updatedEmployee)
    const user = userEvent.setup()

    render(<EmployeeDetailPage />)

    await screen.findByText(/Ing\. Ján Novák/)

    await user.click(screen.getByRole('button', { name: /Upraviť/ }))

    // Submit the form
    await user.click(screen.getByRole('button', { name: /Uložiť zmeny/ }))

    await waitFor(() => {
      expect(mockUpdateEmployee).toHaveBeenCalledWith(
        SAMPLE_EMPLOYEE.id,
        expect.objectContaining({
          first_name: 'Ján',
          last_name: 'Novák',
        }),
      )
    })
  })

  it('opens delete confirmation and deletes employee', async () => {
    mockGetEmployee.mockResolvedValue(SAMPLE_EMPLOYEE)
    mockDeleteEmployee.mockResolvedValue(undefined)
    const user = userEvent.setup()

    render(<EmployeeDetailPage />)

    await screen.findByText(/Ing\. Ján Novák/)

    // Click delete button
    await user.click(screen.getByRole('button', { name: /Zmazať/ }))

    // Confirm dialog appears
    expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()

    // Confirm delete - find the confirm button in the dialog
    const allDeleteButtons = screen.getAllByRole('button', { name: /Zmazať/ })
    await user.click(allDeleteButtons[allDeleteButtons.length - 1]!)

    await waitFor(() => {
      expect(mockDeleteEmployee).toHaveBeenCalledWith(SAMPLE_EMPLOYEE.id)
    })

    expect(mockNavigate).toHaveBeenCalledWith('/employees')
  })

  it('cancels delete confirmation', async () => {
    mockGetEmployee.mockResolvedValue(SAMPLE_EMPLOYEE)
    const user = userEvent.setup()

    render(<EmployeeDetailPage />)

    await screen.findByText(/Ing\. Ján Novák/)

    await user.click(screen.getByRole('button', { name: /Zmazať/ }))
    expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()

    // Cancel
    const cancelButtons = screen.getAllByRole('button', { name: /Zrušiť/ })
    await user.click(cancelButtons[cancelButtons.length - 1]!)

    expect(screen.queryByText('Potvrdiť zmazanie')).not.toBeInTheDocument()
    expect(mockDeleteEmployee).not.toHaveBeenCalled()
  })

  it('displays health insurer name when loaded', async () => {
    mockGetEmployee.mockResolvedValue(SAMPLE_EMPLOYEE)

    render(<EmployeeDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('25 - VšZP')).toBeInTheDocument()
    })
  })
})
