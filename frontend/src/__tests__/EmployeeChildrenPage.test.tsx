import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock service modules before importing component
vi.mock('@/services/employee-child.service', () => ({
  listEmployeeChildren: vi.fn(),
  getEmployeeChild: vi.fn(),
  createEmployeeChild: vi.fn(),
  updateEmployeeChild: vi.fn(),
  deleteEmployeeChild: vi.fn(),
}))

vi.mock('@/services/employee.service', () => ({
  listEmployees: vi.fn(),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ tenantId: 'tenant-aaa' }),
  },
}))

import EmployeeChildrenPage from '@/pages/EmployeeChildrenPage'
import {
  listEmployeeChildren,
  createEmployeeChild,
  updateEmployeeChild,
  deleteEmployeeChild,
} from '@/services/employee-child.service'
import { listEmployees } from '@/services/employee.service'
import type { EmployeeChildRead } from '@/types/employee-child'
import type { EmployeeRead } from '@/types/employee'

const MOCK_CHILD_1: EmployeeChildRead = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-aaa',
  employee_id: 'emp-aaa',
  first_name: 'Ján',
  last_name: 'Novák',
  birth_date: '2020-05-15',
  birth_number: '200515/1234',
  is_tax_bonus_eligible: true,
  custody_from: '2020-05-15',
  custody_to: null,
  created_at: '2025-01-01T08:00:00Z',
  updated_at: '2025-01-01T08:00:00Z',
}

const MOCK_CHILD_2: EmployeeChildRead = {
  id: '22222222-2222-2222-2222-222222222222',
  tenant_id: 'tenant-aaa',
  employee_id: 'emp-aaa',
  first_name: 'Mária',
  last_name: 'Nováková',
  birth_date: '2022-03-10',
  birth_number: null,
  is_tax_bonus_eligible: false,
  custody_from: null,
  custody_to: null,
  created_at: '2025-02-01T08:00:00Z',
  updated_at: '2025-02-01T08:00:00Z',
}

const MOCK_EMPLOYEE: EmployeeRead = {
  id: 'emp-aaa',
  tenant_id: 'tenant-aaa',
  employee_number: 'ZAM-001',
  first_name: 'Peter',
  last_name: 'Kováč',
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
  hire_date: '2020-01-01',
  termination_date: null,
  created_at: '2020-01-01T08:00:00Z',
  updated_at: '2020-01-01T08:00:00Z',
} as EmployeeRead

function mockListResponse(items: EmployeeChildRead[] = [MOCK_CHILD_1, MOCK_CHILD_2]) {
  vi.mocked(listEmployeeChildren).mockResolvedValue({
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

describe('EmployeeChildrenPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListResponse()
    mockEmployees()
  })

  it('renders page heading and data table', async () => {
    render(<EmployeeChildrenPage />)

    expect(screen.getByText('Deti zamestnancov')).toBeInTheDocument()
    expect(screen.getByText('+ Nové dieťa')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    expect(screen.getByText('Nováková Mária')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    vi.mocked(listEmployeeChildren).mockReturnValue(new Promise(() => {}))
    render(<EmployeeChildrenPage />)

    expect(screen.getByText('Načítavam...')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mockListResponse([])
    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Žiadne záznamy')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    vi.mocked(listEmployeeChildren).mockRejectedValue(new Error('Network error'))
    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('displays tax bonus badges correctly', async () => {
    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    const badges = screen.getAllByText(/^(Áno|Nie)$/)
    expect(badges.length).toBeGreaterThanOrEqual(2)
  })

  it('shows employee name from lookup', async () => {
    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    // Employee name should be resolved via lookup
    const employeeCells = screen.getAllByText('Kováč Peter')
    expect(employeeCells.length).toBeGreaterThanOrEqual(1)
  })

  it('opens create modal on button click', async () => {
    const user = userEvent.setup()
    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nové dieťa'))

    expect(screen.getByText('Nové dieťa')).toBeInTheDocument()
    expect(screen.getByText('Vytvoriť')).toBeInTheDocument()
    // Employee dropdown should be visible in create mode
    expect(screen.getByText('— Vyberte zamestnanca —')).toBeInTheDocument()
  })

  it('opens edit modal on Upraviť click', async () => {
    const user = userEvent.setup()
    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upraviť')
    await user.click(editButtons[0]!)

    expect(screen.getByText('Upraviť dieťa')).toBeInTheDocument()
    expect(screen.getByText('Uložiť zmeny')).toBeInTheDocument()
    // Check form is pre-filled
    expect(screen.getByDisplayValue('Ján')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Novák')).toBeInTheDocument()
  })

  it('submits create form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(createEmployeeChild).mockResolvedValue({
      ...MOCK_CHILD_1,
      id: '33333333-3333-3333-3333-333333333333',
      first_name: 'Anna',
      last_name: 'Kováčová',
    })

    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nové dieťa'))

    // Select employee
    const employeeSelect = screen.getByDisplayValue('— Vyberte zamestnanca —')
    await user.selectOptions(employeeSelect, 'emp-aaa')

    // Fill required fields
    await user.type(screen.getByPlaceholderText('napr. Ján'), 'Anna')
    await user.type(screen.getByPlaceholderText('napr. Novák'), 'Kováčová')

    // Fill birth date
    const dateInputs = screen.getAllByDisplayValue('')
    const birthDateInput = dateInputs.find(
      (el) => el.getAttribute('type') === 'date' && el.getAttribute('required') !== null,
    )
    expect(birthDateInput).toBeDefined()
    await user.type(birthDateInput!, '2023-06-01')

    await user.click(screen.getByText('Vytvoriť'))

    await waitFor(() => {
      expect(createEmployeeChild).toHaveBeenCalledTimes(1)
    })

    // List refreshed
    expect(listEmployeeChildren).toHaveBeenCalledTimes(2) // initial + after create
  })

  it('submits edit form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(updateEmployeeChild).mockResolvedValue({
      ...MOCK_CHILD_1,
      first_name: 'Janko',
    })

    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upraviť')
    await user.click(editButtons[0]!)

    // Check pre-filled and submit
    expect(screen.getByDisplayValue('Ján')).toBeInTheDocument()
    await user.click(screen.getByText('Uložiť zmeny'))

    await waitFor(() => {
      expect(updateEmployeeChild).toHaveBeenCalledWith(
        MOCK_CHILD_1.id,
        expect.objectContaining({
          first_name: 'Ján',
          last_name: 'Novák',
        }),
      )
    })
  })

  it('opens and confirms delete dialog', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteEmployeeChild).mockResolvedValue(undefined)

    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
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
      expect(deleteEmployeeChild).toHaveBeenCalledWith(MOCK_CHILD_1.id)
    })
  })

  it('cancels delete dialog', async () => {
    const user = userEvent.setup()

    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazať')
    await user.click(deleteButtons[0]!)

    expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()

    // Click Zrušiť
    const cancelButtons = screen.getAllByText('Zrušiť')
    await user.click(cancelButtons[cancelButtons.length - 1]!)

    expect(screen.queryByText('Potvrdiť zmazanie')).not.toBeInTheDocument()
    expect(deleteEmployeeChild).not.toHaveBeenCalled()
  })

  it('closes create modal on Zrušiť', async () => {
    const user = userEvent.setup()

    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nové dieťa'))
    expect(screen.getByPlaceholderText('napr. Ján')).toBeInTheDocument()

    await user.click(screen.getByText('Zrušiť'))
    expect(screen.queryByPlaceholderText('napr. Ján')).not.toBeInTheDocument()
  })

  it('shows form error on create failure', async () => {
    const user = userEvent.setup()
    vi.mocked(createEmployeeChild).mockRejectedValue(new Error('Duplicitný záznam'))

    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nové dieťa'))

    // Select employee
    const employeeSelect = screen.getByDisplayValue('— Vyberte zamestnanca —')
    await user.selectOptions(employeeSelect, 'emp-aaa')

    // Fill required fields
    await user.type(screen.getByPlaceholderText('napr. Ján'), 'Anna')
    await user.type(screen.getByPlaceholderText('napr. Novák'), 'Kováčová')

    const dateInputs = screen.getAllByDisplayValue('')
    const birthDateInput = dateInputs.find(
      (el) => el.getAttribute('type') === 'date' && el.getAttribute('required') !== null,
    )
    expect(birthDateInput).toBeDefined()
    await user.type(birthDateInput!, '2023-06-01')

    await user.click(screen.getByText('Vytvoriť'))

    await waitFor(() => {
      expect(screen.getByText('Duplicitný záznam')).toBeInTheDocument()
    })
  })

  it('opens detail modal on Detail click', async () => {
    const user = userEvent.setup()

    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    // Detail modal should show sections
    expect(screen.getByText('Osobné údaje')).toBeInTheDocument()
    // 'Zamestnanec' appears in table header too, so check legend specifically
    const legends = screen.getAllByText('Zamestnanec')
    expect(legends.length).toBeGreaterThanOrEqual(2) // table header + detail legend
    expect(screen.getByText('Starostlivosť & bonus')).toBeInTheDocument()
    expect(screen.getByText('Systém')).toBeInTheDocument()
    expect(screen.getByText('Zavrieť')).toBeInTheDocument()
  })

  it('closes detail modal on Zavrieť click', async () => {
    const user = userEvent.setup()

    render(<EmployeeChildrenPage />)

    await waitFor(() => {
      expect(screen.getByText('Novák Ján')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    expect(screen.getByText('Osobné údaje')).toBeInTheDocument()

    await user.click(screen.getByText('Zavrieť'))

    expect(screen.queryByText('Osobné údaje')).not.toBeInTheDocument()
  })
})
