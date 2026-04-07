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
  listEmployeeChildren,
  getEmployeeChild,
  createEmployeeChild,
  updateEmployeeChild,
  deleteEmployeeChild,
} from '@/services/employee-child.service'
import type { EmployeeChildCreate, EmployeeChildUpdate } from '@/types/employee-child'

const mockedApi = vi.mocked(api)

const SAMPLE_CHILD = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: '22222222-2222-2222-2222-222222222222',
  employee_id: '33333333-3333-3333-3333-333333333333',
  first_name: 'Ján',
  last_name: 'Novák',
  birth_date: '2020-05-15',
  birth_number: null,
  is_tax_bonus_eligible: true,
  custody_from: null,
  custody_to: null,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
}

describe('employee-child.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listEmployeeChildren', () => {
    it('calls GET /api/v1/employee-children with pagination params', async () => {
      const paginated = { items: [SAMPLE_CHILD], total: 1, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      const result = await listEmployeeChildren({ skip: 0, limit: 50 })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/employee-children', {
        params: { skip: 0, limit: 50 },
      })
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
    })

    it('passes employee_id filter when provided', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listEmployeeChildren({ skip: 0, limit: 50, employee_id: 'emp-uuid' })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/employee-children', {
        params: { skip: 0, limit: 50, employee_id: 'emp-uuid' },
      })
    })

    it('works without params', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listEmployeeChildren()

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/employee-children', {
        params: undefined,
      })
    })
  })

  describe('getEmployeeChild', () => {
    it('calls GET /api/v1/employee-children/:id', async () => {
      mockedApi.get.mockResolvedValue({ data: SAMPLE_CHILD })

      const result = await getEmployeeChild(SAMPLE_CHILD.id)

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/api/v1/employee-children/${SAMPLE_CHILD.id}`,
      )
      expect(result.first_name).toBe('Ján')
      expect(result.last_name).toBe('Novák')
    })
  })

  describe('createEmployeeChild', () => {
    it('calls POST /api/v1/employee-children with payload', async () => {
      const payload: EmployeeChildCreate = {
        tenant_id: SAMPLE_CHILD.tenant_id,
        employee_id: SAMPLE_CHILD.employee_id,
        first_name: 'Mária',
        last_name: 'Nováková',
        birth_date: '2022-03-10',
        birth_number: '220310/1234',
        is_tax_bonus_eligible: true,
        custody_from: '2022-03-10',
        custody_to: null,
      }
      mockedApi.post.mockResolvedValue({ data: { ...SAMPLE_CHILD, ...payload } })

      const result = await createEmployeeChild(payload)

      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/employee-children', payload)
      expect(result.first_name).toBe('Mária')
    })
  })

  describe('updateEmployeeChild', () => {
    it('calls PATCH /api/v1/employee-children/:id (not PUT)', async () => {
      const payload: EmployeeChildUpdate = {
        first_name: 'Peter',
        is_tax_bonus_eligible: false,
      }
      mockedApi.patch.mockResolvedValue({
        data: { ...SAMPLE_CHILD, ...payload },
      })

      const result = await updateEmployeeChild(SAMPLE_CHILD.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/employee-children/${SAMPLE_CHILD.id}`,
        payload,
      )
      expect(result.first_name).toBe('Peter')
      expect(result.is_tax_bonus_eligible).toBe(false)
    })
  })

  describe('deleteEmployeeChild', () => {
    it('calls DELETE /api/v1/employee-children/:id', async () => {
      mockedApi.delete.mockResolvedValue({ data: undefined })

      await deleteEmployeeChild(SAMPLE_CHILD.id)

      expect(mockedApi.delete).toHaveBeenCalledWith(
        `/api/v1/employee-children/${SAMPLE_CHILD.id}`,
      )
    })
  })
})
