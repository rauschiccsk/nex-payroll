import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock api module before importing the service
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '@/services/api'
import {
  listNotifications,
  getNotification,
  createNotification,
  updateNotification,
  deleteNotification,
  markAsRead,
  getUnreadCount,
} from '@/services/notification.service'
import type { NotificationCreate, NotificationUpdate } from '@/types/notification'

const mockedApi = vi.mocked(api)

const SAMPLE_NOTIFICATION = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: '22222222-2222-2222-2222-222222222222',
  user_id: '33333333-3333-3333-3333-333333333333',
  type: 'deadline' as const,
  severity: 'warning' as const,
  title: 'Termín SP výkazu',
  message: 'Do termínu SP výkazu zostávajú 3 dni.',
  related_entity: 'monthly_report',
  related_entity_id: '44444444-4444-4444-4444-444444444444',
  is_read: false,
  read_at: null,
  created_at: '2026-04-10T08:00:00Z',
}

describe('notification.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listNotifications', () => {
    it('calls GET /api/v1/notifications with params', async () => {
      const paginated = { items: [SAMPLE_NOTIFICATION], total: 1, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      const result = await listNotifications({ skip: 0, limit: 50, is_read: false })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/notifications', {
        params: { skip: 0, limit: 50, is_read: false },
      })
      expect(result).toEqual(paginated)
    })
  })

  describe('getNotification', () => {
    it('calls GET /api/v1/notifications/:id', async () => {
      mockedApi.get.mockResolvedValue({ data: SAMPLE_NOTIFICATION })

      const result = await getNotification(SAMPLE_NOTIFICATION.id)

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/api/v1/notifications/${SAMPLE_NOTIFICATION.id}`,
      )
      expect(result).toEqual(SAMPLE_NOTIFICATION)
    })
  })

  describe('createNotification', () => {
    it('calls POST /api/v1/notifications', async () => {
      const payload: NotificationCreate = {
        tenant_id: '22222222-2222-2222-2222-222222222222',
        user_id: '33333333-3333-3333-3333-333333333333',
        type: 'system',
        severity: 'info',
        title: 'Test',
        message: 'Test message',
      }
      mockedApi.post.mockResolvedValue({ data: { ...SAMPLE_NOTIFICATION, ...payload } })

      const result = await createNotification(payload)

      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/notifications', payload)
      expect(result.title).toBe('Test')
    })
  })

  describe('updateNotification', () => {
    it('calls PATCH /api/v1/notifications/:id', async () => {
      const payload: NotificationUpdate = { is_read: true }
      const updated = { ...SAMPLE_NOTIFICATION, is_read: true }
      mockedApi.patch.mockResolvedValue({ data: updated })

      const result = await updateNotification(SAMPLE_NOTIFICATION.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/notifications/${SAMPLE_NOTIFICATION.id}`,
        payload,
      )
      expect(result.is_read).toBe(true)
    })
  })

  describe('deleteNotification', () => {
    it('calls DELETE /api/v1/notifications/:id', async () => {
      mockedApi.delete.mockResolvedValue({})

      await deleteNotification(SAMPLE_NOTIFICATION.id)

      expect(mockedApi.delete).toHaveBeenCalledWith(
        `/api/v1/notifications/${SAMPLE_NOTIFICATION.id}`,
      )
    })
  })

  describe('markAsRead', () => {
    it('calls PATCH with is_read: true', async () => {
      const updated = { ...SAMPLE_NOTIFICATION, is_read: true, read_at: '2026-04-10T10:00:00Z' }
      mockedApi.patch.mockResolvedValue({ data: updated })

      const result = await markAsRead(SAMPLE_NOTIFICATION.id)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/notifications/${SAMPLE_NOTIFICATION.id}`,
        { is_read: true },
      )
      expect(result.is_read).toBe(true)
    })
  })

  describe('getUnreadCount', () => {
    it('calls GET with user_id and is_read=false and returns total', async () => {
      mockedApi.get.mockResolvedValue({ data: { items: [], total: 5, skip: 0, limit: 0 } })

      const count = await getUnreadCount('user-123')

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/notifications', {
        params: { user_id: 'user-123', is_read: false, limit: 0 },
      })
      expect(count).toBe(5)
    })
  })
})
