import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type { NotificationCreate, NotificationRead, NotificationUpdate } from '@/types/notification'

const BASE = '/api/v1/notifications'

export async function listNotifications(
  params?: PaginationParams & {
    user_id?: string
    is_read?: boolean
    type?: string
    severity?: string
  },
): Promise<PaginatedResponse<NotificationRead>> {
  const response = await api.get<PaginatedResponse<NotificationRead>>(BASE, { params })
  return response.data
}

export async function getNotification(id: string): Promise<NotificationRead> {
  const response = await api.get<NotificationRead>(`${BASE}/${id}`)
  return response.data
}

export async function createNotification(data: NotificationCreate): Promise<NotificationRead> {
  const response = await api.post<NotificationRead>(BASE, data)
  return response.data
}

export async function updateNotification(
  id: string,
  data: NotificationUpdate,
): Promise<NotificationRead> {
  const response = await api.patch<NotificationRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteNotification(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}

/** Mark a single notification as read */
export async function markAsRead(id: string): Promise<NotificationRead> {
  const response = await api.patch<NotificationRead>(`${BASE}/${id}`, { is_read: true })
  return response.data
}

/** Get count of unread notifications for the current user */
export async function getUnreadCount(userId: string): Promise<number> {
  const response = await api.get<PaginatedResponse<NotificationRead>>(BASE, {
    params: { user_id: userId, is_read: false, limit: 0 },
  })
  return response.data.total
}
