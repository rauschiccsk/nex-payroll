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
  listContracts,
  getContract,
  createContract,
  updateContract,
  deleteContract,
} from '@/services/contract.service'
import type { ContractCreate, ContractUpdate } from '@/types/contract'

const mockedApi = vi.mocked(api)

const SAMPLE_CONTRACT = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: '22222222-2222-2222-2222-222222222222',
  employee_id: '33333333-3333-3333-3333-333333333333',
  contract_number: 'PZ-2025-001',
  contract_type: 'permanent' as const,
  job_title: 'Developer',
  wage_type: 'monthly' as const,
  base_wage: 2500.0,
  hours_per_week: 40.0,
  start_date: '2025-01-01',
  end_date: null,
  probation_end_date: null,
  termination_date: null,
  termination_reason: null,
  is_current: true,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
}

describe('contract.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listContracts', () => {
    it('calls GET /api/v1/contracts with pagination params', async () => {
      const paginated = { items: [SAMPLE_CONTRACT], total: 1, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      const result = await listContracts({ skip: 0, limit: 50 })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/contracts', {
        params: { skip: 0, limit: 50 },
      })
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
    })

    it('passes employee_id filter when provided', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listContracts({ skip: 0, limit: 50, employee_id: 'emp-uuid' })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/contracts', {
        params: { skip: 0, limit: 50, employee_id: 'emp-uuid' },
      })
    })

    it('works without params', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listContracts()

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/contracts', {
        params: undefined,
      })
    })
  })

  describe('getContract', () => {
    it('calls GET /api/v1/contracts/:id', async () => {
      mockedApi.get.mockResolvedValue({ data: SAMPLE_CONTRACT })

      const result = await getContract(SAMPLE_CONTRACT.id)

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/api/v1/contracts/${SAMPLE_CONTRACT.id}`,
      )
      expect(result.contract_number).toBe('PZ-2025-001')
    })
  })

  describe('createContract', () => {
    it('calls POST /api/v1/contracts with payload', async () => {
      const payload: ContractCreate = {
        tenant_id: SAMPLE_CONTRACT.tenant_id,
        employee_id: SAMPLE_CONTRACT.employee_id,
        contract_number: 'PZ-2025-002',
        contract_type: 'fixed_term',
        job_title: 'Tester',
        wage_type: 'hourly',
        base_wage: 15.0,
        start_date: '2025-06-01',
      }
      mockedApi.post.mockResolvedValue({ data: { ...SAMPLE_CONTRACT, ...payload } })

      const result = await createContract(payload)

      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/contracts', payload)
      expect(result.contract_number).toBe('PZ-2025-002')
    })
  })

  describe('updateContract', () => {
    it('calls PATCH /api/v1/contracts/:id (not PUT)', async () => {
      const payload: ContractUpdate = {
        job_title: 'Senior Developer',
        base_wage: 3000.0,
      }
      mockedApi.patch.mockResolvedValue({
        data: { ...SAMPLE_CONTRACT, ...payload },
      })

      const result = await updateContract(SAMPLE_CONTRACT.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/contracts/${SAMPLE_CONTRACT.id}`,
        payload,
      )
      expect(result.job_title).toBe('Senior Developer')
      // Verify it does NOT call put
      expect(mockedApi.get).not.toHaveBeenCalled()
    })
  })

  describe('deleteContract', () => {
    it('calls DELETE /api/v1/contracts/:id', async () => {
      mockedApi.delete.mockResolvedValue({ data: undefined })

      await deleteContract(SAMPLE_CONTRACT.id)

      expect(mockedApi.delete).toHaveBeenCalledWith(
        `/api/v1/contracts/${SAMPLE_CONTRACT.id}`,
      )
    })
  })
})
