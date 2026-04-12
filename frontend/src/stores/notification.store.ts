import { createStore } from 'zustand/vanilla'

export interface NotificationState {
  unreadCount: number
  notifications: Array<{ id: string; message: string; read: boolean; created_at: string }>
  setUnreadCount: (count: number) => void
  setNotifications: (items: NotificationState['notifications']) => void
  markRead: (id: string) => void
}

export const notificationStore = createStore<NotificationState>((set) => ({
  unreadCount: 0,
  notifications: [],
  setUnreadCount: (unreadCount) => set({ unreadCount }),
  setNotifications: (notifications) => set({ notifications }),
  markRead: (id) =>
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n,
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    })),
}))
