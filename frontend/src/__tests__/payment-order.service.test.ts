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
  listPaymentOrders,
  getPaymentOrder,
  createPaymentOrder,
  updatePaymentOrder,
  deletePaymentOrder,
} from '@/services/payment-order.service'
import type { PaymentOrderCreate, PaymentOrderUpdate } from '@/types/payment-order'

const mockedApi = vi.mocked(api)

const SAMPLE_ORDER = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: '22222222-2222-2222-2222-222222222222',
  period_year: 2026,
  period_month: 4,
  payment_type: 'net_wage' as const,
  recipient_name: 'Jan Novak',
  recipient_iban: 'SK3112000000198742637541',
  recipient_bic: 'TATRSKBX',
  amount: '1843.04',
  variable_symbol: '0426',
  specific_symbol: null,
  constant_symbol: null,
  reference: null,
  status: 'pending' as const,
  employee_id: '33333333-3333-3333-3333-333333333333',
  health_insurer_id: null,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
}

describe('payment-order.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listPaymentOrders', () => {
    it('calls GET /api/v1/payments with pagination params', async () => {
      const paginated = { items: [SAMPLE_ORDER], total: 1, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      const result = await listPaymentOrders({ skip: 0, limit: 50 })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/payments', {
        params: { skip: 0, limit: 50 },
      })
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
    })

    it('passes filter params when provided', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listPaymentOrders({
        skip: 0,
        limit: 50,
        payment_type: 'sp',
        status: 'pending',
        period_year: 2026,
        period_month: 4,
      })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/payments', {
        params: {
          skip: 0,
          limit: 50,
          payment_type: 'sp',
          status: 'pending',
          period_year: 2026,
          period_month: 4,
        },
      })
    })

    it('works without params', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listPaymentOrders()

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/payments', {
        params: undefined,
      })
    })
  })

  describe('getPaymentOrder', () => {
    it('calls GET /api/v1/payments/:id', async () => {
      mockedApi.get.mockResolvedValue({ data: SAMPLE_ORDER })

      const result = await getPaymentOrder(SAMPLE_ORDER.id)

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/api/v1/payments/${SAMPLE_ORDER.id}`,
      )
      expect(result.recipient_name).toBe('Jan Novak')
      expect(result.amount).toBe('1843.04')
    })
  })

  describe('createPaymentOrder', () => {
    it('calls POST /api/v1/payments with payload', async () => {
      const payload: PaymentOrderCreate = {
        tenant_id: SAMPLE_ORDER.tenant_id,
        period_year: 2026,
        period_month: 4,
        payment_type: 'net_wage',
        recipient_name: 'Jan Novak',
        recipient_iban: 'SK3112000000198742637541',
        amount: '1843.04',
      }
      mockedApi.post.mockResolvedValue({ data: { ...SAMPLE_ORDER, ...payload } })

      const result = await createPaymentOrder(payload)

      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/payments', payload)
      expect(result.payment_type).toBe('net_wage')
    })
  })

  describe('updatePaymentOrder', () => {
    it('calls PATCH /api/v1/payments/:id (not PUT)', async () => {
      const payload: PaymentOrderUpdate = {
        status: 'exported',
        amount: '2000.00',
      }
      mockedApi.patch.mockResolvedValue({
        data: { ...SAMPLE_ORDER, ...payload },
      })

      const result = await updatePaymentOrder(SAMPLE_ORDER.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/payments/${SAMPLE_ORDER.id}`,
        payload,
      )
      expect(result.status).toBe('exported')
      expect(result.amount).toBe('2000.00')
    })
  })

  describe('deletePaymentOrder', () => {
    it('calls DELETE /api/v1/payments/:id', async () => {
      mockedApi.delete.mockResolvedValue({ data: undefined })

      await deletePaymentOrder(SAMPLE_ORDER.id)

      expect(mockedApi.delete).toHaveBeenCalledWith(
        `/api/v1/payments/${SAMPLE_ORDER.id}`,
      )
    })
  })
})
