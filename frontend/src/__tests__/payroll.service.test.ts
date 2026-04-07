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
  listPayrolls,
  getPayroll,
  createPayroll,
  updatePayroll,
  deletePayroll,
} from '@/services/payroll.service'
import type { PayrollCreate, PayrollUpdate } from '@/types/payroll'

const mockedApi = vi.mocked(api)

const SAMPLE_PAYROLL = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: '22222222-2222-2222-2222-222222222222',
  employee_id: '33333333-3333-3333-3333-333333333333',
  contract_id: '44444444-4444-4444-4444-444444444444',
  period_year: 2026,
  period_month: 3,
  status: 'draft' as const,
  base_wage: 2500.0,
  overtime_hours: 0,
  overtime_amount: 0,
  bonus_amount: 0,
  supplement_amount: 0,
  gross_wage: 2500.0,
  sp_assessment_base: 2500.0,
  sp_nemocenske: 35.0,
  sp_starobne: 100.0,
  sp_invalidne: 75.0,
  sp_nezamestnanost: 25.0,
  sp_employee_total: 235.0,
  zp_assessment_base: 2500.0,
  zp_employee: 100.0,
  partial_tax_base: 2165.0,
  nczd_applied: 470.47,
  tax_base: 1694.53,
  tax_advance: 321.96,
  child_bonus: 0,
  tax_after_bonus: 321.96,
  net_wage: 1843.04,
  sp_employer_nemocenske: 35.0,
  sp_employer_starobne: 350.0,
  sp_employer_invalidne: 75.0,
  sp_employer_nezamestnanost: 25.0,
  sp_employer_garancne: 6.25,
  sp_employer_rezervny: 118.75,
  sp_employer_kurzarbeit: 15.0,
  sp_employer_urazove: 20.0,
  sp_employer_total: 645.0,
  zp_employer: 250.0,
  total_employer_cost: 3395.0,
  pillar2_amount: 0,
  ai_validation_result: null,
  ledger_sync_status: null,
  calculated_at: null,
  approved_at: null,
  approved_by: null,
  created_at: '2026-03-01T00:00:00Z',
  updated_at: '2026-03-01T00:00:00Z',
}

describe('payroll.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listPayrolls', () => {
    it('calls GET /api/v1/payrolls with pagination params', async () => {
      const paginated = { items: [SAMPLE_PAYROLL], total: 1, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      const result = await listPayrolls({ skip: 0, limit: 50 })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/payrolls', {
        params: { skip: 0, limit: 50 },
      })
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
    })

    it('passes filter params when provided', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listPayrolls({
        skip: 0,
        limit: 50,
        employee_id: 'emp-uuid',
        period_year: 2026,
        period_month: 3,
        status: 'draft',
      })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/payrolls', {
        params: {
          skip: 0,
          limit: 50,
          employee_id: 'emp-uuid',
          period_year: 2026,
          period_month: 3,
          status: 'draft',
        },
      })
    })

    it('works without params', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listPayrolls()

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/payrolls', {
        params: undefined,
      })
    })
  })

  describe('getPayroll', () => {
    it('calls GET /api/v1/payrolls/:id', async () => {
      mockedApi.get.mockResolvedValue({ data: SAMPLE_PAYROLL })

      const result = await getPayroll(SAMPLE_PAYROLL.id)

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/api/v1/payrolls/${SAMPLE_PAYROLL.id}`,
      )
      expect(result.period_year).toBe(2026)
      expect(result.net_wage).toBe(1843.04)
    })
  })

  describe('createPayroll', () => {
    it('calls POST /api/v1/payrolls with payload', async () => {
      const payload: PayrollCreate = {
        tenant_id: SAMPLE_PAYROLL.tenant_id,
        employee_id: SAMPLE_PAYROLL.employee_id,
        contract_id: SAMPLE_PAYROLL.contract_id,
        period_year: 2026,
        period_month: 4,
        base_wage: 2500.0,
        gross_wage: 2500.0,
        sp_assessment_base: 2500.0,
        sp_nemocenske: 35.0,
        sp_starobne: 100.0,
        sp_invalidne: 75.0,
        sp_nezamestnanost: 25.0,
        sp_employee_total: 235.0,
        zp_assessment_base: 2500.0,
        zp_employee: 100.0,
        partial_tax_base: 2165.0,
        nczd_applied: 470.47,
        tax_base: 1694.53,
        tax_advance: 321.96,
        tax_after_bonus: 321.96,
        net_wage: 1843.04,
        sp_employer_nemocenske: 35.0,
        sp_employer_starobne: 350.0,
        sp_employer_invalidne: 75.0,
        sp_employer_nezamestnanost: 25.0,
        sp_employer_garancne: 6.25,
        sp_employer_rezervny: 118.75,
        sp_employer_kurzarbeit: 15.0,
        sp_employer_urazove: 20.0,
        sp_employer_total: 645.0,
        zp_employer: 250.0,
        total_employer_cost: 3395.0,
      }
      mockedApi.post.mockResolvedValue({ data: { ...SAMPLE_PAYROLL, ...payload } })

      const result = await createPayroll(payload)

      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/payrolls', payload)
      expect(result.period_month).toBe(4)
    })
  })

  describe('updatePayroll', () => {
    it('calls PATCH /api/v1/payrolls/:id (not PUT)', async () => {
      const payload: PayrollUpdate = {
        status: 'calculated',
        base_wage: 3000.0,
      }
      mockedApi.patch.mockResolvedValue({
        data: { ...SAMPLE_PAYROLL, ...payload },
      })

      const result = await updatePayroll(SAMPLE_PAYROLL.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/payrolls/${SAMPLE_PAYROLL.id}`,
        payload,
      )
      expect(result.status).toBe('calculated')
      expect(result.base_wage).toBe(3000.0)
    })
  })

  describe('deletePayroll', () => {
    it('calls DELETE /api/v1/payrolls/:id', async () => {
      mockedApi.delete.mockResolvedValue({ data: undefined })

      await deletePayroll(SAMPLE_PAYROLL.id)

      expect(mockedApi.delete).toHaveBeenCalledWith(
        `/api/v1/payrolls/${SAMPLE_PAYROLL.id}`,
      )
    })
  })
})
