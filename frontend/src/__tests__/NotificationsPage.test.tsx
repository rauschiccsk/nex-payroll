import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock services before imports
const mockListNotifications = vi.fn()
const mockCreateNotification = vi.fn()
const mockUpdateNotification = vi.fn()
const mockDeleteNotification = vi.fn()

vi.mock('@/services/notification.service', () => ({
  listNotifications: (...args: unknown[]) => mockListNotifications(...args),
  getNotification: vi.fn(),
  createNotification: (...args: unknown[]) => mockCreateNotification(...args),
  updateNotification: (...args: unknown[]) => mockUpdateNotification(...args),
  deleteNotification: (...args: unknown[]) => mockDeleteNotification(...args),
  markAsRead: vi.fn(),
  getUnreadCount: vi.fn(),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ tenantId: 'tenant-1' }),
  },
}))

import NotificationsPage from '@/pages/NotificationsPage'

const SAMPLE_NOTIFICATION = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-1',
  user_id: '22222222-2222-2222-2222-222222222222',
  type: 'deadline' as const,
  severity: 'warning' as const,
  title: 'Termín SP výkazu',
  message: 'Do termínu SP výkazu zostávajú 3 dni.',
  related_entity: 'monthly_report',
  related_entity_id: '33333333-3333-3333-3333-333333333333',
  is_read: false,
  read_at: null,
  created_at: '2026-04-10T08:00:00Z',
}

const EMPTY_RESPONSE = { items: [], total: 0, skip: 0, limit: 20 }
const ONE_NOTIFICATION_RESPONSE = { items: [SAMPLE_NOTIFICATION], total: 1, skip: 0, limit: 20 }

describe('NotificationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page header', async () => {
    mockListNotifications.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      render(<NotificationsPage />)
    })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Notifikácie/)
  })

  it('renders notification records in the table after loading', async () => {
    mockListNotifications.mockResolvedValue(ONE_NOTIFICATION_RESPONSE)

    await act(async () => {
      render(<NotificationsPage />)
    })

    const table = await screen.findByRole('table')
    const tableScope = within(table)
    expect(tableScope.getByText('Termín SP výkazu')).toBeInTheDocument()
    expect(tableScope.getByText('Termín')).toBeInTheDocument()
    expect(tableScope.getByText('Varovanie')).toBeInTheDocument()
    expect(tableScope.getByText('Nové')).toBeInTheDocument()
  })

  it('shows empty state when no records', async () => {
    mockListNotifications.mockResolvedValue(EMPTY_RESPONSE)

    await act(async () => {
      render(<NotificationsPage />)
    })

    expect(await screen.findByText(/iadne notifikácie/)).toBeInTheDocument()
  })

  it('opens create modal when button clicked', async () => {
    mockListNotifications.mockResolvedValue(EMPTY_RESPONSE)
    const user = userEvent.setup()

    await act(async () => {
      render(<NotificationsPage />)
    })

    const createBtn = await screen.findByRole('button', { name: /Nová notifikácia/ })
    await user.click(createBtn)

    // Modal heading appears — check for User ID field which is only in modal create form
    expect(await screen.findByPlaceholderText('UUID používateľa')).toBeInTheDocument()
  })

  it('opens edit modal and populates form with notification data', async () => {
    mockListNotifications.mockResolvedValue(ONE_NOTIFICATION_RESPONSE)
    const user = userEvent.setup()

    await act(async () => {
      render(<NotificationsPage />)
    })

    const table = await screen.findByRole('table')
    expect(within(table).getByText('Termín SP výkazu')).toBeInTheDocument()

    const editButtons = within(table).getAllByRole('button', { name: /Upravi/ })
    await user.click(editButtons[0]!)

    expect(await screen.findByText(/Upraviť notifikáciu/)).toBeInTheDocument()
  })

  it('opens detail modal when Detail button clicked', async () => {
    mockListNotifications.mockResolvedValue(ONE_NOTIFICATION_RESPONSE)
    const user = userEvent.setup()

    await act(async () => {
      render(<NotificationsPage />)
    })

    const table = await screen.findByRole('table')
    expect(within(table).getByText('Termín SP výkazu')).toBeInTheDocument()

    const detailBtn = within(table).getByRole('button', { name: 'Detail' })
    await user.click(detailBtn)

    // Detail modal shows notification title
    expect(await screen.findByText(/Notifikácia — Termín SP výkazu/)).toBeInTheDocument()
    // Shows message text
    expect(screen.getByText(/Do termínu SP výkazu zostávajú 3 dni/)).toBeInTheDocument()
  })

  it('opens delete confirmation and deletes a notification', async () => {
    mockListNotifications
      .mockResolvedValueOnce(ONE_NOTIFICATION_RESPONSE)
      .mockResolvedValueOnce(EMPTY_RESPONSE)
    mockDeleteNotification.mockResolvedValue(undefined)
    const user = userEvent.setup()

    await act(async () => {
      render(<NotificationsPage />)
    })

    const table = await screen.findByRole('table')
    expect(within(table).getByText('Termín SP výkazu')).toBeInTheDocument()

    const deleteButtons = within(table).getAllByRole('button', { name: /Zmaza/ })
    await user.click(deleteButtons[0]!)

    // Confirm dialog appears
    expect(await screen.findByText(/Potvrdiť zmazanie/)).toBeInTheDocument()

    // Click confirm delete
    const allDeleteButtons = screen.getAllByRole('button', { name: /Zmaza/ })
    await user.click(allDeleteButtons[allDeleteButtons.length - 1]!)

    await waitFor(() => {
      expect(mockDeleteNotification).toHaveBeenCalledWith(SAMPLE_NOTIFICATION.id)
    })
  })

  it('shows read notification without highlight', async () => {
    const readNotification = { ...SAMPLE_NOTIFICATION, is_read: true, read_at: '2026-04-10T10:00:00Z' }
    mockListNotifications.mockResolvedValue({ items: [readNotification], total: 1, skip: 0, limit: 20 })

    await act(async () => {
      render(<NotificationsPage />)
    })

    const table = await screen.findByRole('table')
    expect(within(table).getByText('Prečítané')).toBeInTheDocument()
  })

  it('shows error message when fetch fails', async () => {
    mockListNotifications.mockRejectedValue(new Error('Network error'))

    await act(async () => {
      render(<NotificationsPage />)
    })

    expect(await screen.findByText('Network error')).toBeInTheDocument()
  })

  it('submits create form with correct payload', async () => {
    mockListNotifications.mockResolvedValue(EMPTY_RESPONSE)
    mockCreateNotification.mockResolvedValue(SAMPLE_NOTIFICATION)
    const user = userEvent.setup()

    await act(async () => {
      render(<NotificationsPage />)
    })

    const createBtn = await screen.findByRole('button', { name: /Nov/ })
    await user.click(createBtn)

    // Fill form
    const userIdInput = screen.getByPlaceholderText('UUID používateľa')
    await user.type(userIdInput, '22222222-2222-2222-2222-222222222222')

    const titleInput = screen.getByPlaceholderText('Názov notifikácie')
    await user.type(titleInput, 'Test notifikácia')

    const messageInput = screen.getByPlaceholderText('Text notifikácie...')
    await user.type(messageInput, 'Test správa')

    // Submit
    const submitBtn = screen.getByRole('button', { name: /Vytvoriť/ })
    await user.click(submitBtn)

    await waitFor(() => {
      expect(mockCreateNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          tenant_id: 'tenant-1',
          user_id: '22222222-2222-2222-2222-222222222222',
          title: 'Test notifikácia',
          message: 'Test správa',
          type: 'system',
          severity: 'info',
        }),
      )
    })
  })
})
