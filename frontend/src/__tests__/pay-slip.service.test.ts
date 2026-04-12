import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock api module before importing the service
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  downloadFile: vi.fn(),
}))

import api from '@/services/api'
import {
  listPaySlips,
  getPaySlip,
  createPaySlip,
  updatePaySlip,
  deletePaySlip,
  downloadPaySlip,
} from '@/services/pay-slip.service'
import { downloadFile } from '@/services/api'
import type { PaySlipCreate, PaySlipUpdate } from '@/types/pay-slip'

const mockedApi = vi.mocked(api)
const mockedDownloadFile = vi.mocked(downloadFile)

const SAMPLE_SLIP = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: '22222222-2222-2222-2222-222222222222',
  payroll_id: '33333333-3333-3333-3333-333333333333',
  employee_id: '44444444-4444-4444-4444-444444444444',
  period_year: 2026,
  period_month: 3,
  pdf_path: '/payslips/2026/03/E001.pdf',
  file_size_bytes: 45200,
  generated_at: '2026-03-15T10:00:00Z',
  downloaded_at: null,
  created_at: '2026-03-15T10:00:00Z',
  updated_at: '2026-03-15T10:00:00Z',
}

describe('pay-slip.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listPaySlips', () => {
    it('calls GET /api/v1/payslips with pagination params', async () => {
      const paginated = { items: [SAMPLE_SLIP], total: 1, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      const result = await listPaySlips({ skip: 0, limit: 50 })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/payslips', {
        params: { skip: 0, limit: 50 },
      })
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
    })

    it('passes filter params when provided', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listPaySlips({
        skip: 0,
        limit: 50,
        employee_id: SAMPLE_SLIP.employee_id,
        period_year: 2026,
        period_month: 3,
      })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/payslips', {
        params: {
          skip: 0,
          limit: 50,
          employee_id: SAMPLE_SLIP.employee_id,
          period_year: 2026,
          period_month: 3,
        },
      })
    })

    it('works without params', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listPaySlips()

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/payslips', {
        params: undefined,
      })
    })
  })

  describe('getPaySlip', () => {
    it('calls GET /api/v1/payslips/:id', async () => {
      mockedApi.get.mockResolvedValue({ data: SAMPLE_SLIP })

      const result = await getPaySlip(SAMPLE_SLIP.id)

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/api/v1/payslips/${SAMPLE_SLIP.id}`,
      )
      expect(result.pdf_path).toBe('/payslips/2026/03/E001.pdf')
      expect(result.file_size_bytes).toBe(45200)
    })
  })

  describe('createPaySlip', () => {
    it('calls POST /api/v1/payslips with payload', async () => {
      const payload: PaySlipCreate = {
        payroll_id: SAMPLE_SLIP.payroll_id,
        employee_id: SAMPLE_SLIP.employee_id,
        period_year: 2026,
        period_month: 3,
        pdf_path: '/payslips/2026/03/E001.pdf',
        file_size_bytes: 45200,
      }
      mockedApi.post.mockResolvedValue({ data: { ...SAMPLE_SLIP, ...payload } })

      const result = await createPaySlip(payload)

      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/payslips', payload)
      expect(result.period_year).toBe(2026)
    })
  })

  describe('updatePaySlip', () => {
    it('calls PATCH /api/v1/payslips/:id with only updatable fields', async () => {
      const payload: PaySlipUpdate = {
        pdf_path: '/payslips/2026/03/E001_v2.pdf',
        file_size_bytes: 52000,
      }
      mockedApi.patch.mockResolvedValue({
        data: { ...SAMPLE_SLIP, ...payload },
      })

      const result = await updatePaySlip(SAMPLE_SLIP.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/payslips/${SAMPLE_SLIP.id}`,
        payload,
      )
      expect(result.pdf_path).toBe('/payslips/2026/03/E001_v2.pdf')
      expect(result.file_size_bytes).toBe(52000)
    })
  })

  describe('deletePaySlip', () => {
    it('calls DELETE /api/v1/payslips/:id', async () => {
      mockedApi.delete.mockResolvedValue({ data: undefined })

      await deletePaySlip(SAMPLE_SLIP.id)

      expect(mockedApi.delete).toHaveBeenCalledWith(
        `/api/v1/payslips/${SAMPLE_SLIP.id}`,
      )
    })
  })

  describe('downloadPaySlip', () => {
    it('calls downloadFile with correct URL and default filename', async () => {
      mockedDownloadFile.mockResolvedValue(undefined)

      await downloadPaySlip(SAMPLE_SLIP.id)

      expect(mockedDownloadFile).toHaveBeenCalledWith(
        `/api/v1/payslips/${SAMPLE_SLIP.id}/download`,
        `payslip-${SAMPLE_SLIP.id}.pdf`,
      )
    })

    it('uses custom filename when provided', async () => {
      mockedDownloadFile.mockResolvedValue(undefined)

      await downloadPaySlip(SAMPLE_SLIP.id, 'custom-name.pdf')

      expect(mockedDownloadFile).toHaveBeenCalledWith(
        `/api/v1/payslips/${SAMPLE_SLIP.id}/download`,
        'custom-name.pdf',
      )
    })
  })
})
