import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock the service module
vi.mock('@/services/audit-log.service', () => ({
  listAuditLogs: vi.fn(),
  getAuditLog: vi.fn(),
}))

import AuditLogsPage from '@/pages/AuditLogsPage'
import { listAuditLogs } from '@/services/audit-log.service'
import type { AuditLogRead } from '@/types/audit-log'

const MOCK_ENTRY_1: AuditLogRead = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'aaaa-bbbb-cccc-dddd',
  user_id: 'user-1111-2222-3333',
  action: 'CREATE',
  entity_type: 'employees',
  entity_id: 'emp-1111-2222-3333',
  old_values: null,
  new_values: { first_name: 'Ján', last_name: 'Novák' },
  ip_address: '192.168.1.10',
  created_at: '2025-06-15T10:30:00Z',
}

const MOCK_ENTRY_2: AuditLogRead = {
  id: '22222222-2222-2222-2222-222222222222',
  tenant_id: 'aaaa-bbbb-cccc-dddd',
  user_id: null,
  action: 'DELETE',
  entity_type: 'contracts',
  entity_id: 'con-4444-5555-6666',
  old_values: { contract_number: 'C-001' },
  new_values: null,
  ip_address: null,
  created_at: '2025-06-16T14:00:00Z',
}

function mockListResponse(items: AuditLogRead[] = [MOCK_ENTRY_1, MOCK_ENTRY_2]) {
  vi.mocked(listAuditLogs).mockResolvedValue({
    items,
    total: items.length,
    skip: 0,
    limit: 20,
  })
}

describe('AuditLogsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListResponse()
  })

  it('renders page heading and data table', async () => {
    render(<AuditLogsPage />)

    expect(screen.getByText('Audit log')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('employees')).toBeInTheDocument()
    })

    expect(screen.getByText('contracts')).toBeInTheDocument()
    // Labels appear in both filter dropdown options and row badges
    expect(screen.getAllByText('Vytvorenie').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Zmazanie').length).toBeGreaterThanOrEqual(1)
  })

  it('does NOT render create, edit, or delete buttons', async () => {
    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('employees')).toBeInTheDocument()
    })

    // No create button
    expect(screen.queryByText('+ Nový záznam')).not.toBeInTheDocument()
    expect(screen.queryByText('+ Novy zaznam')).not.toBeInTheDocument()

    // No edit/delete buttons in rows
    expect(screen.queryByText('Upraviť')).not.toBeInTheDocument()
    expect(screen.queryByText('Zmazať')).not.toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    vi.mocked(listAuditLogs).mockReturnValue(new Promise(() => {}))
    render(<AuditLogsPage />)

    expect(screen.getByText('Načítavam...')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mockListResponse([])
    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('Žiadne záznamy v audit logu')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    vi.mocked(listAuditLogs).mockRejectedValue(new Error('Network error'))
    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('displays action badges with correct labels', async () => {
    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('Vytvorenie')).toBeInTheDocument()
    })

    // Zmazanie appears in both filter dropdown and badge — check at least one exists
    expect(screen.getAllByText('Zmazanie').length).toBeGreaterThanOrEqual(1)
  })

  it('shows IP address and dash for missing user', async () => {
    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('192.168.1.10')).toBeInTheDocument()
    })

    // user_id null and ip_address null both render as em-dash
    const dashes = screen.getAllByText('\u2014')
    expect(dashes.length).toBeGreaterThanOrEqual(2)
  })

  it('opens detail modal on Zobraziť click', async () => {
    const user = userEvent.setup()
    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('employees')).toBeInTheDocument()
    })

    const viewButtons = screen.getAllByText('Zobraziť')
    await user.click(viewButtons[0]!)

    // Detail modal should show
    expect(screen.getByText('Detail audit záznamu')).toBeInTheDocument()
    expect(screen.getByText(MOCK_ENTRY_1.id)).toBeInTheDocument()
    expect(screen.getByText(MOCK_ENTRY_1.tenant_id)).toBeInTheDocument()
  })

  it('closes detail modal on Zavrieť click', async () => {
    const user = userEvent.setup()
    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('employees')).toBeInTheDocument()
    })

    const viewButtons = screen.getAllByText('Zobraziť')
    await user.click(viewButtons[0]!)

    expect(screen.getByText('Detail audit záznamu')).toBeInTheDocument()

    await user.click(screen.getByText('Zavrieť'))

    expect(screen.queryByText('Detail audit záznamu')).not.toBeInTheDocument()
  })

  it('filters by action', async () => {
    const user = userEvent.setup()
    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('employees')).toBeInTheDocument()
    })

    // Change action filter
    const actionSelect = screen.getByRole('combobox')
    await user.selectOptions(actionSelect, 'CREATE')

    await waitFor(() => {
      expect(listAuditLogs).toHaveBeenCalledWith(
        expect.objectContaining({ action: 'CREATE' }),
      )
    })
  })

  it('clears filters when button clicked', async () => {
    const user = userEvent.setup()
    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('employees')).toBeInTheDocument()
    })

    // Set a filter to make clear button appear
    const actionSelect = screen.getByRole('combobox')
    await user.selectOptions(actionSelect, 'DELETE')

    await waitFor(() => {
      expect(screen.getByText('Zrušiť filtre')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Zrušiť filtre'))

    // Filter reset — listAuditLogs called again without action filter
    await waitFor(() => {
      const lastCall = vi.mocked(listAuditLogs).mock.calls.at(-1)?.[0] as Record<string, unknown> | undefined
      expect(lastCall?.action).toBeUndefined()
    })
  })

  it('shows detail with old_values and new_values JSON', async () => {
    const user = userEvent.setup()
    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('employees')).toBeInTheDocument()
    })

    const viewButtons = screen.getAllByText('Zobraziť')
    await user.click(viewButtons[0]!)

    // new_values should be displayed as JSON
    expect(screen.getByText(/Ján/)).toBeInTheDocument()
    expect(screen.getByText(/Novák/)).toBeInTheDocument()
  })
})
