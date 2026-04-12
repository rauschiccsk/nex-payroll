import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock the service modules before importing component
vi.mock('@/services/contract.service', () => ({
  listContracts: vi.fn(),
  getContract: vi.fn(),
  createContract: vi.fn(),
  updateContract: vi.fn(),
  deleteContract: vi.fn(),
}))

vi.mock('@/services/employee.service', () => ({
  listEmployees: vi.fn(),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ tenantId: 'tenant-aaa' }),
  },
}))

import ContractsPage from '@/pages/ContractsPage'
import {
  listContracts,
  createContract,
  updateContract,
  deleteContract,
} from '@/services/contract.service'
import { listEmployees } from '@/services/employee.service'
import type { ContractRead } from '@/types/contract'
import type { EmployeeRead } from '@/types/employee'

const MOCK_CONTRACT_1: ContractRead = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-aaa',
  employee_id: 'emp-aaa',
  contract_number: 'PZ-2025-001',
  contract_type: 'permanent',
  job_title: 'Softvérový vývojár',
  wage_type: 'monthly',
  base_wage: '2500.00',
  hours_per_week: '40.0',
  start_date: '2025-01-01',
  end_date: null,
  probation_end_date: '2025-04-01',
  termination_date: null,
  termination_reason: null,
  is_current: true,
  created_at: '2025-01-01T08:00:00Z',
  updated_at: '2025-01-01T08:00:00Z',
}

const MOCK_CONTRACT_2: ContractRead = {
  id: '22222222-2222-2222-2222-222222222222',
  tenant_id: 'tenant-aaa',
  employee_id: 'emp-bbb',
  contract_number: 'DPP-2024-010',
  contract_type: 'agreement_work',
  job_title: 'Brigádnik',
  wage_type: 'hourly',
  base_wage: '8.50',
  hours_per_week: '20.0',
  start_date: '2024-06-01',
  end_date: '2024-12-31',
  probation_end_date: null,
  termination_date: '2024-12-31',
  termination_reason: 'Uplynutie doby',
  is_current: false,
  created_at: '2024-06-01T08:00:00Z',
  updated_at: '2024-12-31T08:00:00Z',
}

const MOCK_EMPLOYEE: EmployeeRead = {
  id: 'emp-aaa',
  tenant_id: 'tenant-aaa',
  employee_number: 'ZAM-001',
  first_name: 'Ján',
  last_name: 'Novák',
  title_before: null,
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
  bank_bic: null,
  health_insurer_id: 'hi-aaa',
  tax_declaration_type: 'standard',
  nczd_applied: true,
  pillar2_saver: false,
  is_disabled: false,
  status: 'active',
  hire_date: '2025-01-01',
  termination_date: null,
  created_at: '2025-01-01T08:00:00Z',
  updated_at: '2025-01-01T08:00:00Z',
} as EmployeeRead

function mockListResponse(items: ContractRead[] = [MOCK_CONTRACT_1, MOCK_CONTRACT_2]) {
  vi.mocked(listContracts).mockResolvedValue({
    items,
    total: items.length,
    skip: 0,
    limit: 20,
  })
}

function mockEmployees(items: EmployeeRead[] = [MOCK_EMPLOYEE]) {
  vi.mocked(listEmployees).mockResolvedValue({
    items,
    total: items.length,
    skip: 0,
    limit: 100,
  })
}

describe('ContractsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListResponse()
    mockEmployees()
  })

  it('renders page heading and data table', async () => {
    render(<ContractsPage />)

    expect(screen.getByText('Zmluvy')).toBeInTheDocument()
    expect(screen.getByText('+ Nová zmluva')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    expect(screen.getByText('DPP-2024-010')).toBeInTheDocument()
    expect(screen.getByText('Softvérový vývojár')).toBeInTheDocument()
    expect(screen.getByText('Brigádnik')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    vi.mocked(listContracts).mockReturnValue(new Promise(() => {}))
    render(<ContractsPage />)

    expect(screen.getByText('Načítavam...')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mockListResponse([])
    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('Žiadne zmluvy')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    vi.mocked(listContracts).mockRejectedValue(new Error('Network error'))
    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('displays contract type badges', async () => {
    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('Trvalý pomer')).toBeInTheDocument()
    })

    expect(screen.getByText('Dohoda o práci')).toBeInTheDocument()
  })

  it('displays active/inactive status badges', async () => {
    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('Aktívna')).toBeInTheDocument()
    })

    expect(screen.getByText('Ukončená')).toBeInTheDocument()
  })

  it('opens create modal on button click', async () => {
    const user = userEvent.setup()
    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nová zmluva'))

    expect(screen.getByText('Nová zmluva')).toBeInTheDocument()
    expect(screen.getByText('Vytvoriť')).toBeInTheDocument()
    // Employee dropdown should be visible in create mode
    expect(screen.getByText('Zamestnanec')).toBeInTheDocument()
  })

  it('opens edit modal on Upraviť click', async () => {
    const user = userEvent.setup()
    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upraviť')
    await user.click(editButtons[0]!)

    expect(screen.getByText('Upraviť zmluvu')).toBeInTheDocument()
    expect(screen.getByText('Uložiť zmeny')).toBeInTheDocument()
    // Check form is pre-filled
    expect(screen.getByDisplayValue('PZ-2025-001')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Softvérový vývojár')).toBeInTheDocument()
  })

  it('submits create form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(createContract).mockResolvedValue({
      ...MOCK_CONTRACT_1,
      id: '33333333-3333-3333-3333-333333333333',
      contract_number: 'PZ-2025-002',
    })

    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nová zmluva'))

    // Select employee from dropdown
    const employeeSelect = screen.getByDisplayValue('— Vyberte zamestnanca —')
    await user.selectOptions(employeeSelect, 'emp-aaa')

    // Fill required fields
    await user.type(screen.getByPlaceholderText('napr. PZ-2024-001'), 'PZ-2025-002')
    await user.type(screen.getByPlaceholderText('napr. Softvérový vývojár'), 'Tester')
    await user.type(screen.getByPlaceholderText('napr. 1500.00'), '1800')

    // Fill start date
    const dateInputs = screen.getAllByDisplayValue('')
    // The start_date input is the first empty date input
    const startDateInput = dateInputs.find(
      (el) => el.getAttribute('type') === 'date' && el.getAttribute('required') !== null,
    )
    expect(startDateInput).toBeDefined()
    await user.type(startDateInput!, '2025-03-01')

    await user.click(screen.getByText('Vytvoriť'))

    await waitFor(() => {
      expect(createContract).toHaveBeenCalledTimes(1)
    })

    // List refreshed
    expect(listContracts).toHaveBeenCalledTimes(2) // initial + after create
  })

  it('submits edit form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(updateContract).mockResolvedValue({
      ...MOCK_CONTRACT_1,
      job_title: 'Senior vývojár',
    })

    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upraviť')
    await user.click(editButtons[0]!)

    // Check pre-filled and submit
    expect(screen.getByDisplayValue('PZ-2025-001')).toBeInTheDocument()
    await user.click(screen.getByText('Uložiť zmeny'))

    await waitFor(() => {
      expect(updateContract).toHaveBeenCalledWith(
        MOCK_CONTRACT_1.id,
        expect.objectContaining({
          contract_number: 'PZ-2025-001',
          job_title: 'Softvérový vývojár',
        }),
      )
    })
  })

  it('opens and confirms delete dialog', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteContract).mockResolvedValue(undefined)

    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazať')
    await user.click(deleteButtons[0]!)

    // Confirm dialog
    expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()

    // Find the Zmazať button inside the confirmation dialog
    const confirmButton = screen.getAllByText('Zmazať').find(
      (btn) => btn.closest('.max-w-sm') !== null,
    )
    expect(confirmButton).toBeDefined()
    await user.click(confirmButton!)

    await waitFor(() => {
      expect(deleteContract).toHaveBeenCalledWith(MOCK_CONTRACT_1.id)
    })
  })

  it('cancels delete dialog', async () => {
    const user = userEvent.setup()

    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazať')
    await user.click(deleteButtons[0]!)

    expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()

    // Click Zrušiť
    const cancelButtons = screen.getAllByText('Zrušiť')
    await user.click(cancelButtons[cancelButtons.length - 1]!)

    expect(screen.queryByText('Potvrdiť zmazanie')).not.toBeInTheDocument()
    expect(deleteContract).not.toHaveBeenCalled()
  })

  it('closes create modal on Zrušiť', async () => {
    const user = userEvent.setup()

    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nová zmluva'))
    expect(screen.getByPlaceholderText('napr. PZ-2024-001')).toBeInTheDocument()

    await user.click(screen.getByText('Zrušiť'))
    expect(screen.queryByPlaceholderText('napr. PZ-2024-001')).not.toBeInTheDocument()
  })

  it('shows form error on create failure', async () => {
    const user = userEvent.setup()
    vi.mocked(createContract).mockRejectedValue(new Error('Duplicitné číslo zmluvy'))

    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nová zmluva'))

    // Select employee from dropdown
    const employeeSelect = screen.getByDisplayValue('— Vyberte zamestnanca —')
    await user.selectOptions(employeeSelect, 'emp-aaa')

    // Fill required fields
    await user.type(screen.getByPlaceholderText('napr. PZ-2024-001'), 'PZ-2025-001')
    await user.type(screen.getByPlaceholderText('napr. Softvérový vývojár'), 'Tester')
    await user.type(screen.getByPlaceholderText('napr. 1500.00'), '1800')

    // Fill start date
    const dateInputs = screen.getAllByDisplayValue('')
    const startDateInput = dateInputs.find(
      (el) => el.getAttribute('type') === 'date' && el.getAttribute('required') !== null,
    )
    expect(startDateInput).toBeDefined()
    await user.type(startDateInput!, '2025-03-01')

    await user.click(screen.getByText('Vytvoriť'))

    await waitFor(() => {
      expect(screen.getByText('Duplicitné číslo zmluvy')).toBeInTheDocument()
    })
  })

  it('opens detail modal on Detail click', async () => {
    const user = userEvent.setup()

    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    // Detail modal should show contract info sections
    expect(screen.getByText('Základné údaje')).toBeInTheDocument()
    expect(screen.getByText('Dátumy')).toBeInTheDocument()
    expect(screen.getByText('Systém')).toBeInTheDocument()
    expect(screen.getByText('Zavrieť')).toBeInTheDocument()
  })

  it('closes detail modal on Zavrieť click', async () => {
    const user = userEvent.setup()

    render(<ContractsPage />)

    await waitFor(() => {
      expect(screen.getByText('PZ-2025-001')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    expect(screen.getByText('Základné údaje')).toBeInTheDocument()

    await user.click(screen.getByText('Zavrieť'))

    expect(screen.queryByText('Základné údaje')).not.toBeInTheDocument()
  })
})
