import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock service modules before importing component
vi.mock('@/services/leave-entitlement.service', () => ({
  listLeaveEntitlements: vi.fn(),
  getLeaveEntitlement: vi.fn(),
  createLeaveEntitlement: vi.fn(),
  updateLeaveEntitlement: vi.fn(),
  deleteLeaveEntitlement: vi.fn(),
}))

vi.mock('@/services/employee.service', () => ({
  listEmployees: vi.fn(),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ tenantId: 'tenant-aaa' }),
  },
}))

import LeaveEntitlementsPage from '@/pages/LeaveEntitlementsPage'
import {
  listLeaveEntitlements,
  createLeaveEntitlement,
  updateLeaveEntitlement,
  deleteLeaveEntitlement,
} from '@/services/leave-entitlement.service'
import { listEmployees } from '@/services/employee.service'
import type { LeaveEntitlementRead } from '@/types/leave-entitlement'
import type { EmployeeRead } from '@/types/employee'

const MOCK_ENTITLEMENT_1: LeaveEntitlementRead = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-aaa',
  employee_id: 'emp-aaa',
  year: 2026,
  total_days: 25,
  used_days: 10,
  remaining_days: 15,
  carryover_days: 5,
  created_at: '2026-01-01T08:00:00Z',
  updated_at: '2026-01-01T08:00:00Z',
}

const MOCK_ENTITLEMENT_2: LeaveEntitlementRead = {
  id: '22222222-2222-2222-2222-222222222222',
  tenant_id: 'tenant-aaa',
  employee_id: 'emp-aaa',
  year: 2025,
  total_days: 20,
  used_days: 20,
  remaining_days: 0,
  carryover_days: 0,
  created_at: '2025-01-01T08:00:00Z',
  updated_at: '2025-12-31T08:00:00Z',
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

function mockListResponse(items: LeaveEntitlementRead[] = [MOCK_ENTITLEMENT_1, MOCK_ENTITLEMENT_2]) {
  vi.mocked(listLeaveEntitlements).mockResolvedValue({
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

describe('LeaveEntitlementsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListResponse()
    mockEmployees()
  })

  it('renders page heading and data table', async () => {
    render(<LeaveEntitlementsPage />)

    expect(screen.getByText('Nároky na dovolenku')).toBeInTheDocument()
    expect(screen.getByText('+ Nový nárok')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    expect(screen.getByText('2025')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    vi.mocked(listLeaveEntitlements).mockReturnValue(new Promise(() => {}))
    render(<LeaveEntitlementsPage />)

    expect(screen.getByText('Načítavam...')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mockListResponse([])
    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('Žiadne záznamy')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    vi.mocked(listLeaveEntitlements).mockRejectedValue(new Error('Network error'))
    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('displays remaining days with correct badge colors', async () => {
    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    // remaining_days > 0 → green badge
    const greenBadge = screen.getByText('15')
    expect(greenBadge.className).toContain('bg-green-100')

    // remaining_days === 0 → gray badge
    const grayBadge = screen.getByText('0', { selector: 'span' })
    expect(grayBadge.className).toContain('bg-gray-100')
  })

  it('shows employee name from lookup', async () => {
    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    // Employee name should be resolved via lookup
    const employeeCells = screen.getAllByText('Kováč Peter')
    expect(employeeCells.length).toBeGreaterThanOrEqual(1)
  })

  it('opens create modal on button click', async () => {
    const user = userEvent.setup()
    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nový nárok'))

    expect(screen.getByText('Nový nárok na dovolenku')).toBeInTheDocument()
    expect(screen.getByText('Vytvoriť')).toBeInTheDocument()
    // Employee dropdown should be visible in create mode
    expect(screen.getByText('— Vyberte zamestnanca —')).toBeInTheDocument()
  })

  it('opens edit modal on Upraviť click', async () => {
    const user = userEvent.setup()
    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upraviť')
    await user.click(editButtons[0]!)

    expect(screen.getByText('Upraviť nárok')).toBeInTheDocument()
    expect(screen.getByText('Uložiť zmeny')).toBeInTheDocument()
    // Check form is pre-filled with total_days
    expect(screen.getByDisplayValue('25')).toBeInTheDocument()
    expect(screen.getByDisplayValue('10')).toBeInTheDocument()
  })

  it('submits create form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(createLeaveEntitlement).mockResolvedValue({
      ...MOCK_ENTITLEMENT_1,
      id: '33333333-3333-3333-3333-333333333333',
      year: 2027,
    })

    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nový nárok'))

    // Select employee
    const employeeSelect = screen.getByDisplayValue('— Vyberte zamestnanca —')
    await user.selectOptions(employeeSelect, 'emp-aaa')

    await user.click(screen.getByText('Vytvoriť'))

    await waitFor(() => {
      expect(createLeaveEntitlement).toHaveBeenCalledTimes(1)
    })

    // List refreshed
    expect(listLeaveEntitlements).toHaveBeenCalledTimes(2) // initial + after create
  })

  it('submits edit form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(updateLeaveEntitlement).mockResolvedValue({
      ...MOCK_ENTITLEMENT_1,
      total_days: 30,
      remaining_days: 20,
    })

    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upraviť')
    await user.click(editButtons[0]!)

    // Check pre-filled and submit
    expect(screen.getByDisplayValue('25')).toBeInTheDocument()
    await user.click(screen.getByText('Uložiť zmeny'))

    await waitFor(() => {
      expect(updateLeaveEntitlement).toHaveBeenCalledWith(
        MOCK_ENTITLEMENT_1.id,
        expect.objectContaining({
          total_days: 25,
          used_days: 10,
        }),
      )
    })
  })

  it('opens and confirms delete dialog', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteLeaveEntitlement).mockResolvedValue(undefined)

    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
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
      expect(deleteLeaveEntitlement).toHaveBeenCalledWith(MOCK_ENTITLEMENT_1.id)
    })
  })

  it('cancels delete dialog', async () => {
    const user = userEvent.setup()

    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazať')
    await user.click(deleteButtons[0]!)

    expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()

    // Click Zrušiť
    const cancelButtons = screen.getAllByText('Zrušiť')
    await user.click(cancelButtons[cancelButtons.length - 1]!)

    expect(screen.queryByText('Potvrdiť zmazanie')).not.toBeInTheDocument()
    expect(deleteLeaveEntitlement).not.toHaveBeenCalled()
  })

  it('closes create modal on Zrušiť', async () => {
    const user = userEvent.setup()

    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nový nárok'))
    expect(screen.getByText('Nový nárok na dovolenku')).toBeInTheDocument()

    await user.click(screen.getByText('Zrušiť'))
    expect(screen.queryByText('Nový nárok na dovolenku')).not.toBeInTheDocument()
  })

  it('shows form error on create failure', async () => {
    const user = userEvent.setup()
    vi.mocked(createLeaveEntitlement).mockRejectedValue(new Error('Duplicitný záznam'))

    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nový nárok'))

    // Select employee
    const employeeSelect = screen.getByDisplayValue('— Vyberte zamestnanca —')
    await user.selectOptions(employeeSelect, 'emp-aaa')

    await user.click(screen.getByText('Vytvoriť'))

    await waitFor(() => {
      expect(screen.getByText('Duplicitný záznam')).toBeInTheDocument()
    })
  })

  it('opens detail modal on Detail click', async () => {
    const user = userEvent.setup()

    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    // Detail modal should show sections
    expect(screen.getByText('Dni dovolenky')).toBeInTheDocument()
    // 'Zamestnanec' appears in table header too, so check legend specifically
    const legends = screen.getAllByText('Zamestnanec')
    expect(legends.length).toBeGreaterThanOrEqual(2) // table header + detail legend
    expect(screen.getByText('Systém')).toBeInTheDocument()
    expect(screen.getByText('Zavrieť')).toBeInTheDocument()
  })

  it('closes detail modal on Zavrieť click', async () => {
    const user = userEvent.setup()

    render(<LeaveEntitlementsPage />)

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    expect(screen.getByText('Dni dovolenky')).toBeInTheDocument()

    await user.click(screen.getByText('Zavrieť'))

    expect(screen.queryByText('Dni dovolenky')).not.toBeInTheDocument()
  })
})
