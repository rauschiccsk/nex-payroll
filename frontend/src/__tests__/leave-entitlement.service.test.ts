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
  listLeaveEntitlements,
  getLeaveEntitlement,
  createLeaveEntitlement,
  updateLeaveEntitlement,
  deleteLeaveEntitlement,
} from '@/services/leave-entitlement.service'
import type {
  LeaveEntitlementCreate,
  LeaveEntitlementUpdate,
} from '@/types/leave-entitlement'

const mockedApi = vi.mocked(api)

const SAMPLE_ENTITLEMENT = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: '22222222-2222-2222-2222-222222222222',
  employee_id: '33333333-3333-3333-3333-333333333333',
  year: 2026,
  total_days: 25,
  used_days: 5,
  remaining_days: 20,
  carryover_days: 3,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('leave-entitlement.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listLeaveEntitlements', () => {
    it('calls GET /api/v1/leave-entitlements with pagination params', async () => {
      const paginated = { items: [SAMPLE_ENTITLEMENT], total: 1, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      const result = await listLeaveEntitlements({ skip: 0, limit: 50 })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/leave-entitlements', {
        params: { skip: 0, limit: 50 },
      })
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
    })

    it('passes employee_id and year filters when provided', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listLeaveEntitlements({ skip: 0, limit: 50, employee_id: 'emp-uuid', year: 2026 })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/leave-entitlements', {
        params: { skip: 0, limit: 50, employee_id: 'emp-uuid', year: 2026 },
      })
    })

    it('works without params', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listLeaveEntitlements()

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/leave-entitlements', {
        params: undefined,
      })
    })
  })

  describe('getLeaveEntitlement', () => {
    it('calls GET /api/v1/leave-entitlements/:id', async () => {
      mockedApi.get.mockResolvedValue({ data: SAMPLE_ENTITLEMENT })

      const result = await getLeaveEntitlement(SAMPLE_ENTITLEMENT.id)

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/api/v1/leave-entitlements/${SAMPLE_ENTITLEMENT.id}`,
      )
      expect(result.year).toBe(2026)
      expect(result.total_days).toBe(25)
    })
  })

  describe('createLeaveEntitlement', () => {
    it('calls POST /api/v1/leave-entitlements with payload', async () => {
      const payload: LeaveEntitlementCreate = {
        tenant_id: SAMPLE_ENTITLEMENT.tenant_id,
        employee_id: SAMPLE_ENTITLEMENT.employee_id,
        year: 2026,
        total_days: 20,
        remaining_days: 20,
      }
      mockedApi.post.mockResolvedValue({ data: { ...SAMPLE_ENTITLEMENT, ...payload } })

      const result = await createLeaveEntitlement(payload)

      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/leave-entitlements', payload)
      expect(result.total_days).toBe(20)
    })
  })

  describe('updateLeaveEntitlement', () => {
    it('calls PATCH /api/v1/leave-entitlements/:id (not PUT)', async () => {
      const payload: LeaveEntitlementUpdate = {
        total_days: 30,
        used_days: 10,
      }
      mockedApi.patch.mockResolvedValue({
        data: { ...SAMPLE_ENTITLEMENT, ...payload },
      })

      const result = await updateLeaveEntitlement(SAMPLE_ENTITLEMENT.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/leave-entitlements/${SAMPLE_ENTITLEMENT.id}`,
        payload,
      )
      expect(result.total_days).toBe(30)
      // Verify it does NOT call put — patch is the correct method
      expect(mockedApi.patch).toHaveBeenCalledTimes(1)
    })
  })

  describe('deleteLeaveEntitlement', () => {
    it('calls DELETE /api/v1/leave-entitlements/:id', async () => {
      mockedApi.delete.mockResolvedValue({ data: undefined })

      await deleteLeaveEntitlement(SAMPLE_ENTITLEMENT.id)

      expect(mockedApi.delete).toHaveBeenCalledWith(
        `/api/v1/leave-entitlements/${SAMPLE_ENTITLEMENT.id}`,
      )
    })
  })
})
