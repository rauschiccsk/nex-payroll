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
  listUsers,
  getUser,
  createUser,
  updateUser,
  deleteUser,
} from '@/services/user.service'
import type { UserCreate, UserUpdate } from '@/types/user'

const mockedApi = vi.mocked(api)

const SAMPLE_USER = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: '22222222-2222-2222-2222-222222222222',
  employee_id: null,
  username: 'jnovak',
  email: 'jan.novak@example.com',
  role: 'accountant' as const,
  is_active: true,
  last_login_at: null,
  password_changed_at: null,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
}

describe('user.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listUsers', () => {
    it('calls GET /api/v1/users with pagination params', async () => {
      const paginated = { items: [SAMPLE_USER], total: 1, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      const result = await listUsers({ skip: 0, limit: 50 })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/users', {
        params: { skip: 0, limit: 50 },
      })
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
    })

    it('works without params', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listUsers()

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/users', {
        params: undefined,
      })
    })
  })

  describe('getUser', () => {
    it('calls GET /api/v1/users/:id', async () => {
      mockedApi.get.mockResolvedValue({ data: SAMPLE_USER })

      const result = await getUser(SAMPLE_USER.id)

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/api/v1/users/${SAMPLE_USER.id}`,
      )
      expect(result.username).toBe('jnovak')
    })
  })

  describe('createUser', () => {
    it('calls POST /api/v1/users with payload', async () => {
      const payload: UserCreate = {
        tenant_id: SAMPLE_USER.tenant_id,
        username: 'pnovak',
        email: 'peter.novak@example.com',
        password: 'SecurePass123!',
        role: 'employee',
        employee_id: '33333333-3333-3333-3333-333333333333',
      }
      mockedApi.post.mockResolvedValue({ data: { ...SAMPLE_USER, ...payload } })

      const result = await createUser(payload)

      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/users', payload)
      expect(result.username).toBe('pnovak')
    })
  })

  describe('updateUser', () => {
    it('calls PATCH /api/v1/users/:id with payload', async () => {
      const payload: UserUpdate = {
        role: 'director',
        is_active: false,
      }
      mockedApi.patch.mockResolvedValue({
        data: { ...SAMPLE_USER, ...payload },
      })

      const result = await updateUser(SAMPLE_USER.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/users/${SAMPLE_USER.id}`,
        payload,
      )
      expect(result.role).toBe('director')
      expect(result.is_active).toBe(false)
    })

    it('sends only changed fields (partial update)', async () => {
      const payload: UserUpdate = { email: 'new@example.com' }
      mockedApi.patch.mockResolvedValue({
        data: { ...SAMPLE_USER, email: 'new@example.com' },
      })

      await updateUser(SAMPLE_USER.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/users/${SAMPLE_USER.id}`,
        { email: 'new@example.com' },
      )
    })
  })

  describe('deleteUser', () => {
    it('calls DELETE /api/v1/users/:id', async () => {
      mockedApi.delete.mockResolvedValue({ data: undefined })

      await deleteUser(SAMPLE_USER.id)

      expect(mockedApi.delete).toHaveBeenCalledWith(
        `/api/v1/users/${SAMPLE_USER.id}`,
      )
    })
  })
})
