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
  listLeaves,
  getLeave,
  createLeave,
  updateLeave,
  deleteLeave,
} from '@/services/leave.service'
import type { LeaveCreate, LeaveUpdate } from '@/types/leave'

const mockedApi = vi.mocked(api)

const SAMPLE_LEAVE = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: '22222222-2222-2222-2222-222222222222',
  employee_id: '33333333-3333-3333-3333-333333333333',
  leave_type: 'annual' as const,
  start_date: '2026-04-01',
  end_date: '2026-04-10',
  business_days: 8,
  status: 'pending' as const,
  note: null,
  approved_by: null,
  approved_at: null,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
}

describe('leave.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listLeaves', () => {
    it('calls GET /api/v1/leaves with params', async () => {
      const paginated = { items: [SAMPLE_LEAVE], total: 1, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      const result = await listLeaves({ skip: 0, limit: 50, status: 'pending' })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/leaves', {
        params: { skip: 0, limit: 50, status: 'pending' },
      })
      expect(result).toEqual(paginated)
    })
  })

  describe('getLeave', () => {
    it('calls GET /api/v1/leaves/:id', async () => {
      mockedApi.get.mockResolvedValue({ data: SAMPLE_LEAVE })

      const result = await getLeave(SAMPLE_LEAVE.id)

      expect(mockedApi.get).toHaveBeenCalledWith(`/api/v1/leaves/${SAMPLE_LEAVE.id}`)
      expect(result).toEqual(SAMPLE_LEAVE)
    })
  })

  describe('createLeave', () => {
    it('calls POST /api/v1/leaves', async () => {
      const payload: LeaveCreate = {
        tenant_id: SAMPLE_LEAVE.tenant_id,
        employee_id: SAMPLE_LEAVE.employee_id,
        leave_type: 'annual',
        start_date: '2026-04-01',
        end_date: '2026-04-10',
        business_days: 8,
      }
      mockedApi.post.mockResolvedValue({ data: SAMPLE_LEAVE })

      const result = await createLeave(payload)

      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/leaves', payload)
      expect(result).toEqual(SAMPLE_LEAVE)
    })
  })

  describe('updateLeave', () => {
    it('calls PATCH /api/v1/leaves/:id', async () => {
      const payload: LeaveUpdate = { status: 'approved' }
      const updated = { ...SAMPLE_LEAVE, status: 'approved' as const }
      mockedApi.patch.mockResolvedValue({ data: updated })

      const result = await updateLeave(SAMPLE_LEAVE.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/leaves/${SAMPLE_LEAVE.id}`,
        payload,
      )
      expect(result.status).toBe('approved')
    })
  })

  describe('deleteLeave', () => {
    it('calls DELETE /api/v1/leaves/:id', async () => {
      mockedApi.delete.mockResolvedValue({ data: undefined })

      await deleteLeave(SAMPLE_LEAVE.id)

      expect(mockedApi.delete).toHaveBeenCalledWith(`/api/v1/leaves/${SAMPLE_LEAVE.id}`)
    })
  })
})
