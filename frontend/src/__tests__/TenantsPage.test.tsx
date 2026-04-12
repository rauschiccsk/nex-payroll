import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock the service module
vi.mock('@/services/tenant.service', () => ({
  listTenants: vi.fn(),
  getTenant: vi.fn(),
  createTenant: vi.fn(),
  updateTenant: vi.fn(),
  deleteTenant: vi.fn(),
}))

import TenantsPage from '@/pages/TenantsPage'
import {
  listTenants,
  createTenant,
  updateTenant,
  deleteTenant,
} from '@/services/tenant.service'
import type { TenantRead } from '@/types/tenant'

const MOCK_TENANT_1: TenantRead = {
  id: '11111111-1111-1111-1111-111111111111',
  name: 'Alpha s.r.o.',
  ico: '12345678',
  dic: '2012345678',
  ic_dph: 'SK2012345678',
  address_street: 'Hlavna 1',
  address_city: 'Bratislava',
  address_zip: '81101',
  address_country: 'SK',
  bank_iban: 'SK3112000000198742637541',
  bank_bic: 'SUBASKBX',
  schema_name: 'tenant_12345678',
  default_role: 'accountant',
  is_active: true,
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
}

const MOCK_TENANT_2: TenantRead = {
  id: '22222222-2222-2222-2222-222222222222',
  name: 'Beta a.s.',
  ico: '87654321',
  dic: null,
  ic_dph: null,
  address_street: 'Nova 5',
  address_city: 'Kosice',
  address_zip: '04001',
  address_country: 'SK',
  bank_iban: 'SK3112000000198742637542',
  bank_bic: null,
  schema_name: 'tenant_87654321',
  default_role: 'director',
  is_active: false,
  created_at: '2025-02-01T08:00:00Z',
  updated_at: '2025-02-01T08:00:00Z',
}

function mockListResponse(items: TenantRead[] = [MOCK_TENANT_1, MOCK_TENANT_2]) {
  vi.mocked(listTenants).mockResolvedValue({
    items,
    total: items.length,
    skip: 0,
    limit: 20,
  })
}

describe('TenantsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListResponse()
  })

  it('renders page heading and data table', async () => {
    render(<TenantsPage />)

    expect(screen.getByText('Organizacie')).toBeInTheDocument()
    expect(screen.getByText('+ Nova organizacia')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Alpha s.r.o.')).toBeInTheDocument()
    })

    expect(screen.getByText('Beta a.s.')).toBeInTheDocument()
    expect(screen.getByText('12345678')).toBeInTheDocument()
    expect(screen.getByText('87654321')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    // Make list hang so we can see loading state
    vi.mocked(listTenants).mockReturnValue(new Promise(() => {}))
    render(<TenantsPage />)

    expect(screen.getByText('Nacitavam...')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mockListResponse([])
    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Ziadne organizacie')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    vi.mocked(listTenants).mockRejectedValue(new Error('Network error'))
    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('displays active/inactive status badges', async () => {
    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Alpha s.r.o.')).toBeInTheDocument()
    })

    expect(screen.getByText('Aktivna')).toBeInTheDocument()
    expect(screen.getByText('Neaktivna')).toBeInTheDocument()
  })

  it('opens create modal on button click', async () => {
    const user = userEvent.setup()
    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Alpha s.r.o.')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nova organizacia'))

    expect(screen.getByText('Nova organizacia')).toBeInTheDocument()
    expect(screen.getByText('Vytvorit')).toBeInTheDocument()
  })

  it('opens edit modal on Upravit click', async () => {
    const user = userEvent.setup()
    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Alpha s.r.o.')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upravit')
    await user.click(editButtons[0]!)

    expect(screen.getByText('Upravit organizaciu')).toBeInTheDocument()
    expect(screen.getByText('Ulozit zmeny')).toBeInTheDocument()
    // Check form is pre-filled
    expect(screen.getByDisplayValue('Alpha s.r.o.')).toBeInTheDocument()
    expect(screen.getByDisplayValue('12345678')).toBeInTheDocument()
  })

  it('submits create form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(createTenant).mockResolvedValue({
      ...MOCK_TENANT_1,
      id: '33333333-3333-3333-3333-333333333333',
      name: 'Gamma s.r.o.',
    })

    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Alpha s.r.o.')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nova organizacia'))

    // Fill required fields
    await user.type(screen.getByPlaceholderText('napr. Firma s.r.o.'), 'Gamma s.r.o.')
    await user.type(screen.getByPlaceholderText('napr. 12345678'), '11223344')
    await user.type(screen.getByPlaceholderText('napr. Hlavna 1'), 'Dlha 10')
    await user.type(screen.getByPlaceholderText('napr. Bratislava'), 'Zilina')
    await user.type(screen.getByPlaceholderText('napr. 81101'), '01001')
    await user.type(screen.getByPlaceholderText('SK...'), 'SK3112000000198742637543')

    await user.click(screen.getByText('Vytvorit'))

    await waitFor(() => {
      expect(createTenant).toHaveBeenCalledTimes(1)
    })

    // List refreshed
    expect(listTenants).toHaveBeenCalledTimes(2) // initial + after create
  })

  it('submits edit form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(updateTenant).mockResolvedValue({
      ...MOCK_TENANT_1,
      name: 'Alpha Updated s.r.o.',
    })

    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Alpha s.r.o.')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upravit')
    await user.click(editButtons[0]!)

    // Check pre-filled value
    expect(screen.getByDisplayValue('Alpha s.r.o.')).toBeInTheDocument()

    // Submit with existing values
    await user.click(screen.getByText('Ulozit zmeny'))

    await waitFor(() => {
      expect(updateTenant).toHaveBeenCalledWith(
        MOCK_TENANT_1.id,
        expect.objectContaining({
          name: 'Alpha s.r.o.',
          ico: '12345678',
        }),
      )
    })
  })

  it('opens and confirms delete dialog', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteTenant).mockResolvedValue(undefined)

    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Alpha s.r.o.')).toBeInTheDocument()
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
      expect(deleteTenant).toHaveBeenCalledWith(MOCK_TENANT_1.id)
    })
  })

  it('cancels delete dialog', async () => {
    const user = userEvent.setup()

    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Alpha s.r.o.')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazat')
    await user.click(deleteButtons[0]!)

    expect(screen.getByText('Potvrdit zmazanie')).toBeInTheDocument()

    // Click Zrusit
    const cancelButtons = screen.getAllByText('Zrusit')
    await user.click(cancelButtons[cancelButtons.length - 1]!)

    expect(screen.queryByText('Potvrdit zmazanie')).not.toBeInTheDocument()
    expect(deleteTenant).not.toHaveBeenCalled()
  })

  it('closes create modal on Zrusit', async () => {
    const user = userEvent.setup()

    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Alpha s.r.o.')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nova organizacia'))
    // The modal title is "Nova organizacia" — same as the page heading text
    // but the modal should have specific form elements
    expect(screen.getByPlaceholderText('napr. Firma s.r.o.')).toBeInTheDocument()

    await user.click(screen.getByText('Zrusit'))
    expect(screen.queryByPlaceholderText('napr. Firma s.r.o.')).not.toBeInTheDocument()
  })

  it('shows form error on create failure', async () => {
    const user = userEvent.setup()
    vi.mocked(createTenant).mockRejectedValue(new Error('ICO already exists'))

    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Alpha s.r.o.')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nova organizacia'))

    // Fill required fields
    await user.type(screen.getByPlaceholderText('napr. Firma s.r.o.'), 'Dup Firma')
    await user.type(screen.getByPlaceholderText('napr. 12345678'), '12345678')
    await user.type(screen.getByPlaceholderText('napr. Hlavna 1'), 'Test 1')
    await user.type(screen.getByPlaceholderText('napr. Bratislava'), 'Test')
    await user.type(screen.getByPlaceholderText('napr. 81101'), '00000')
    await user.type(screen.getByPlaceholderText('SK...'), 'SK0000000000000000000000')

    await user.click(screen.getByText('Vytvorit'))

    await waitFor(() => {
      expect(screen.getByText('ICO already exists')).toBeInTheDocument()
    })
  })

  it('displays city and IBAN in table rows', async () => {
    render(<TenantsPage />)

    await waitFor(() => {
      expect(screen.getByText('Bratislava')).toBeInTheDocument()
    })

    expect(screen.getByText('Kosice')).toBeInTheDocument()
    expect(screen.getByText('SK3112000000198742637541')).toBeInTheDocument()
    expect(screen.getByText('SK3112000000198742637542')).toBeInTheDocument()
  })
})
