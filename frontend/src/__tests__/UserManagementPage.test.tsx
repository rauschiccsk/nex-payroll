import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock service modules before importing component
vi.mock('@/services/user.service', () => ({
  listUsers: vi.fn(),
  getUser: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ tenantId: 'tenant-aaa' }),
  },
}))

import UserManagementPage from '@/pages/UserManagementPage'
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
} from '@/services/user.service'
import type { UserRead } from '@/types/user'

const MOCK_USER_1: UserRead = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-aaa',
  employee_id: 'emp-aaa',
  username: 'jan.novak',
  email: 'jan.novak@firma.sk',
  role: 'director',
  is_active: true,
  last_login_at: '2025-06-15T10:30:00Z',
  password_changed_at: '2025-06-01T08:00:00Z',
  created_at: '2025-01-01T08:00:00Z',
  updated_at: '2025-06-15T10:30:00Z',
}

const MOCK_USER_2: UserRead = {
  id: '22222222-2222-2222-2222-222222222222',
  tenant_id: 'tenant-aaa',
  employee_id: null,
  username: 'maria.kovacova',
  email: 'maria.kovacova@firma.sk',
  role: 'accountant',
  is_active: false,
  last_login_at: null,
  password_changed_at: null,
  created_at: '2025-02-01T08:00:00Z',
  updated_at: '2025-02-01T08:00:00Z',
}

function mockListResponse(items: UserRead[] = [MOCK_USER_1, MOCK_USER_2]) {
  vi.mocked(listUsers).mockResolvedValue({
    items,
    total: items.length,
    skip: 0,
    limit: 20,
  })
}

describe('UserManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListResponse()
  })

  it('renders page heading and data table', async () => {
    render(<UserManagementPage />)

    expect(screen.getByText('Sprava pouzivatelov')).toBeInTheDocument()
    expect(screen.getByText('+ Novy pouzivatel')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    expect(screen.getByText('maria.kovacova')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    vi.mocked(listUsers).mockReturnValue(new Promise(() => {}))
    render(<UserManagementPage />)

    expect(screen.getByText('Nacitavam...')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mockListResponse([])
    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('Ziadni pouzivatelia')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    vi.mocked(listUsers).mockRejectedValue(new Error('Network error'))
    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('displays role badges correctly', async () => {
    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    expect(screen.getByText('Riaditel')).toBeInTheDocument()
    expect(screen.getByText('Uctovnik')).toBeInTheDocument()
  })

  it('displays active/inactive status badges', async () => {
    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    expect(screen.getByText('Aktivny')).toBeInTheDocument()
    expect(screen.getByText('Neaktivny')).toBeInTheDocument()
  })

  it('opens create modal on button click', async () => {
    const user = userEvent.setup()
    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Novy pouzivatel'))

    expect(screen.getByText('Novy pouzivatel')).toBeInTheDocument()
    expect(screen.getByText('Vytvorit')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('napr. jan.novak')).toBeInTheDocument()
  })

  it('opens edit modal on Upravit click', async () => {
    const user = userEvent.setup()
    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upravit')
    await user.click(editButtons[0]!)

    expect(screen.getByText('Upravit pouzivatela')).toBeInTheDocument()
    expect(screen.getByText('Ulozit zmeny')).toBeInTheDocument()
    // Check form is pre-filled
    expect(screen.getByDisplayValue('jan.novak')).toBeInTheDocument()
    expect(screen.getByDisplayValue('jan.novak@firma.sk')).toBeInTheDocument()
  })

  it('submits create form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(createUser).mockResolvedValue({
      ...MOCK_USER_1,
      id: '33333333-3333-3333-3333-333333333333',
      username: 'peter.horvath',
      email: 'peter.horvath@firma.sk',
    })

    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Novy pouzivatel'))

    // Fill required fields
    await user.type(screen.getByPlaceholderText('napr. jan.novak'), 'peter.horvath')
    await user.type(
      screen.getByPlaceholderText('napr. jan.novak@firma.sk'),
      'peter.horvath@firma.sk',
    )
    await user.type(screen.getByPlaceholderText('Zadajte heslo'), 'SecurePass123!')

    await user.click(screen.getByText('Vytvorit'))

    await waitFor(() => {
      expect(createUser).toHaveBeenCalledTimes(1)
    })

    // List refreshed
    expect(listUsers).toHaveBeenCalledTimes(2) // initial + after create
  })

  it('submits edit form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(updateUser).mockResolvedValue({
      ...MOCK_USER_1,
      username: 'jan.novak.updated',
    })

    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upravit')
    await user.click(editButtons[0]!)

    // Check pre-filled and submit
    expect(screen.getByDisplayValue('jan.novak')).toBeInTheDocument()
    await user.click(screen.getByText('Ulozit zmeny'))

    await waitFor(() => {
      expect(updateUser).toHaveBeenCalledWith(MOCK_USER_1.id, expect.any(Object))
    })
  })

  it('opens and confirms delete dialog', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteUser).mockResolvedValue(undefined)

    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazat')
    await user.click(deleteButtons[0]!)

    // Confirm dialog
    expect(screen.getByText('Potvrdit zmazanie')).toBeInTheDocument()

    // Find the Zmazat button inside the confirmation dialog
    const confirmButton = screen
      .getAllByText('Zmazat')
      .find((btn) => btn.closest('.max-w-sm') !== null)
    expect(confirmButton).toBeDefined()
    await user.click(confirmButton!)

    await waitFor(() => {
      expect(deleteUser).toHaveBeenCalledWith(MOCK_USER_1.id)
    })
  })

  it('cancels delete dialog', async () => {
    const user = userEvent.setup()

    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazat')
    await user.click(deleteButtons[0]!)

    expect(screen.getByText('Potvrdit zmazanie')).toBeInTheDocument()

    // Click Zrusit
    const cancelButtons = screen.getAllByText('Zrusit')
    await user.click(cancelButtons[cancelButtons.length - 1]!)

    expect(screen.queryByText('Potvrdit zmazanie')).not.toBeInTheDocument()
    expect(deleteUser).not.toHaveBeenCalled()
  })

  it('closes create modal on Zrusit', async () => {
    const user = userEvent.setup()

    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Novy pouzivatel'))
    expect(screen.getByPlaceholderText('napr. jan.novak')).toBeInTheDocument()

    await user.click(screen.getByText('Zrusit'))
    expect(screen.queryByPlaceholderText('napr. jan.novak')).not.toBeInTheDocument()
  })

  it('shows form error on create failure', async () => {
    const user = userEvent.setup()
    vi.mocked(createUser).mockRejectedValue(new Error('Pouzivatel uz existuje'))

    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Novy pouzivatel'))

    // Fill required fields
    await user.type(screen.getByPlaceholderText('napr. jan.novak'), 'peter.horvath')
    await user.type(
      screen.getByPlaceholderText('napr. jan.novak@firma.sk'),
      'peter.horvath@firma.sk',
    )
    await user.type(screen.getByPlaceholderText('Zadajte heslo'), 'SecurePass123!')

    await user.click(screen.getByText('Vytvorit'))

    await waitFor(() => {
      expect(screen.getByText('Pouzivatel uz existuje')).toBeInTheDocument()
    })
  })

  it('opens detail modal on username click', async () => {
    const user = userEvent.setup()

    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    await user.click(screen.getByText('jan.novak'))

    expect(screen.getByText('Detail pouzivatela')).toBeInTheDocument()
    // Email appears in both table and detail modal
    const emailElements = screen.getAllByText('jan.novak@firma.sk')
    expect(emailElements.length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('Zavriet')).toBeInTheDocument()
  })

  it('opens detail modal on Detail button click', async () => {
    const user = userEvent.setup()

    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    expect(screen.getByText('Detail pouzivatela')).toBeInTheDocument()
    expect(screen.getByText('Zavriet')).toBeInTheDocument()
  })

  it('closes detail modal on Zavriet click', async () => {
    const user = userEvent.setup()

    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    expect(screen.getByText('Detail pouzivatela')).toBeInTheDocument()

    await user.click(screen.getByText('Zavriet'))

    expect(screen.queryByText('Detail pouzivatela')).not.toBeInTheDocument()
  })

  it('password field is optional in edit mode', async () => {
    const user = userEvent.setup()

    render(<UserManagementPage />)

    await waitFor(() => {
      expect(screen.getByText('jan.novak')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upravit')
    await user.click(editButtons[0]!)

    // Password field should have placeholder indicating it's optional
    expect(screen.getByPlaceholderText('(bez zmeny)')).toBeInTheDocument()
    // Password field should not be required in edit mode
    const passwordInput = screen.getByPlaceholderText('(bez zmeny)')
    expect(passwordInput).not.toBeRequired()
  })
})
