import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock services
const mockListEmployees = vi.fn()
const mockCreateEmployee = vi.fn()
const mockUpdateEmployee = vi.fn()
const mockDeleteEmployee = vi.fn()
const mockListHealthInsurers = vi.fn()

vi.mock('@/services/employee.service', () => ({
  listEmployees: (...args: unknown[]) => mockListEmployees(...args),
  createEmployee: (...args: unknown[]) => mockCreateEmployee(...args),
  updateEmployee: (...args: unknown[]) => mockUpdateEmployee(...args),
  deleteEmployee: (...args: unknown[]) => mockDeleteEmployee(...args),
  getEmployee: vi.fn(),
}))

vi.mock('@/services/health-insurer.service', () => ({
  listHealthInsurers: (...args: unknown[]) => mockListHealthInsurers(...args),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ token: 'test-token', tenantId: 'tenant-123' }),
  },
}))

import EmployeesPage from '@/pages/EmployeesPage'
import type { EmployeeRead } from '@/types/employee'

const SAMPLE_EMPLOYEE: EmployeeRead = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-123',
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

const SAMPLE_EMPLOYEE_2: EmployeeRead = {
  ...SAMPLE_EMPLOYEE,
  id: '22222222-2222-2222-2222-222222222222',
  employee_number: 'E002',
  first_name: 'Mária',
  last_name: 'Kováčová',
  title_before: null,
  title_after: null,
  gender: 'F',
  status: 'inactive',
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

describe('EmployeesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListEmployees.mockResolvedValue({
      items: [SAMPLE_EMPLOYEE, SAMPLE_EMPLOYEE_2],
      total: 2,
      skip: 0,
      limit: 20,
    })
    mockListHealthInsurers.mockResolvedValue({
      items: [SAMPLE_INSURER],
      total: 1,
      skip: 0,
      limit: 100,
    })
  })

  it('renders employee list with correct data', async () => {
    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText('Zamestnanci')).toBeInTheDocument()
    })

    expect(screen.getByText('E001')).toBeInTheDocument()
    expect(screen.getByText('E002')).toBeInTheDocument()
    expect(screen.getByText(/Ing\. Ján Novák/)).toBeInTheDocument()
    expect(screen.getByText('Mária Kováčová')).toBeInTheDocument()
  })

  it('shows status badges with correct labels', async () => {
    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText('Aktívny')).toBeInTheDocument()
    })
    expect(screen.getByText('Neaktívny')).toBeInTheDocument()
  })

  it('shows empty state when no employees', async () => {
    mockListEmployees.mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 20,
    })

    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText('Žiadni zamestnanci')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    mockListEmployees.mockRejectedValue(new Error('Network error'))

    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('opens detail modal when clicking employee name', async () => {
    const user = userEvent.setup()

    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText(/Ing\. Ján Novák/)).toBeInTheDocument()
    })

    // Click the employee name link
    await user.click(screen.getByText(/Ing\. Ján Novák/))

    // Detail modal should show personal info
    await waitFor(() => {
      expect(screen.getByText('Osobné údaje')).toBeInTheDocument()
    })
    expect(screen.getByText('Číslo zamestnanca:')).toBeInTheDocument()
    expect(screen.getByText('900115/1234')).toBeInTheDocument()
  })

  it('opens create form without tenant_id input', async () => {
    const user = userEvent.setup()

    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText('+ Nový zamestnanec')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nový zamestnanec'))

    await waitFor(() => {
      expect(screen.getByText('Nový zamestnanec')).toBeInTheDocument()
    })

    // Tenant ID field must NOT be present — it comes from auth context
    expect(screen.queryByText('Tenant ID')).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText('UUID organizácie')).not.toBeInTheDocument()

    // Regular form fields should be present
    expect(screen.getByText('Číslo zamestnanca')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('napr. Ján')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('napr. Novák')).toBeInTheDocument()
  })

  it('create form does not expose tenant_id field — uses auth store', async () => {
    const user = userEvent.setup()

    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText('+ Nový zamestnanec')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nový zamestnanec'))

    await waitFor(() => {
      expect(screen.getByText('Nový zamestnanec')).toBeInTheDocument()
    })

    // Tenant ID field must NOT exist in the form
    expect(screen.queryByText('Tenant ID')).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText('UUID organizácie')).not.toBeInTheDocument()

    // The form should have standard employee fields
    expect(screen.getByPlaceholderText('napr. EMP001')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('napr. Ján')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('napr. Novák')).toBeInTheDocument()
  })

  it('opens edit modal for existing employee', async () => {
    const user = userEvent.setup()

    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getAllByText('Upraviť').length).toBeGreaterThan(0)
    })

    // Click first "Upraviť" button in table
    await user.click(screen.getAllByText('Upraviť')[0]!)

    await waitFor(() => {
      expect(screen.getByText('Upraviť zamestnanca')).toBeInTheDocument()
    })

    // Should pre-fill form with employee data
    expect(screen.getByDisplayValue('E001')).toBeInTheDocument()
  })

  it('shows delete confirmation dialog', async () => {
    const user = userEvent.setup()

    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getAllByText('Zmazať').length).toBeGreaterThan(0)
    })

    // Click first delete button
    await user.click(screen.getAllByText('Zmazať')[0]!)

    await waitFor(() => {
      expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()
    })
    expect(screen.getByText(/Naozaj chcete zmazať zamestnanca/)).toBeInTheDocument()
  })

  it('deletes employee after confirmation', async () => {
    const user = userEvent.setup()
    mockDeleteEmployee.mockResolvedValue(undefined)

    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getAllByText('Zmazať').length).toBeGreaterThan(0)
    })

    // Click first delete button in table
    const deleteButtons = screen.getAllByText('Zmazať')
    await user.click(deleteButtons[0]!)

    await waitFor(() => {
      expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()
    })

    // Confirm deletion — find the "Zmazať" button inside the confirmation dialog
    const confirmDeleteBtn = screen.getAllByText('Zmazať').find(
      (btn) => btn.closest('.max-w-sm') !== null
    )
    if (confirmDeleteBtn) {
      await user.click(confirmDeleteBtn)
    }

    await waitFor(() => {
      expect(mockDeleteEmployee).toHaveBeenCalledWith(SAMPLE_EMPLOYEE.id)
    })
  })

  it('displays health insurer name from lookup', async () => {
    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getAllByText('25 - VšZP').length).toBeGreaterThan(0)
    })
  })

  it('uses correct Slovak diacritics in detail view', async () => {
    const user = userEvent.setup()

    await act(async () => {
      render(<EmployeesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText(/Ing\. Ján Novák/)).toBeInTheDocument()
    })

    // Open detail
    await user.click(screen.getByText(/Ing\. Ján Novák/))

    await waitFor(() => {
      expect(screen.getByText(/NCZD:.*Áno/)).toBeInTheDocument()
    })
    expect(screen.getByText(/ZŤP:.*Áno|ZŤP:.*Nie/)).toBeInTheDocument()
  })
})
