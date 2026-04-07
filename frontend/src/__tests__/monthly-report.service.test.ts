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
  listMonthlyReports,
  getMonthlyReport,
  createMonthlyReport,
  updateMonthlyReport,
  deleteMonthlyReport,
} from '@/services/monthly-report.service'
import type { MonthlyReportCreate, MonthlyReportUpdate } from '@/types/monthly-report'

const mockedApi = vi.mocked(api)

const SAMPLE_REPORT = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  tenant_id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  period_year: 2026,
  period_month: 3,
  report_type: 'sp_monthly' as const,
  file_path: '/reports/2026/03/sp_monthly.xml',
  file_format: 'xml' as const,
  status: 'generated' as const,
  deadline_date: '2026-04-20',
  institution: 'Socialna poistovna',
  submitted_at: null,
  health_insurer_id: null,
  created_at: '2026-03-01T00:00:00Z',
  updated_at: '2026-03-01T00:00:00Z',
}

describe('monthly-report.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listMonthlyReports', () => {
    it('calls GET /api/v1/monthly-reports with pagination params', async () => {
      const paginated = { items: [SAMPLE_REPORT], total: 1, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      const result = await listMonthlyReports({ skip: 0, limit: 50 })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/monthly-reports', {
        params: { skip: 0, limit: 50 },
      })
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
    })

    it('passes filter params when provided', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listMonthlyReports({
        skip: 0,
        limit: 50,
        report_type: 'sp_monthly',
        status: 'generated',
        period_year: 2026,
        period_month: 3,
      })

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/monthly-reports', {
        params: {
          skip: 0,
          limit: 50,
          report_type: 'sp_monthly',
          status: 'generated',
          period_year: 2026,
          period_month: 3,
        },
      })
    })

    it('works without params', async () => {
      const paginated = { items: [], total: 0, skip: 0, limit: 50 }
      mockedApi.get.mockResolvedValue({ data: paginated })

      await listMonthlyReports()

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/monthly-reports', {
        params: undefined,
      })
    })
  })

  describe('getMonthlyReport', () => {
    it('calls GET /api/v1/monthly-reports/:id', async () => {
      mockedApi.get.mockResolvedValue({ data: SAMPLE_REPORT })

      const result = await getMonthlyReport(SAMPLE_REPORT.id)

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/api/v1/monthly-reports/${SAMPLE_REPORT.id}`,
      )
      expect(result.report_type).toBe('sp_monthly')
    })
  })

  describe('createMonthlyReport', () => {
    it('calls POST /api/v1/monthly-reports with payload', async () => {
      const payload: MonthlyReportCreate = {
        tenant_id: SAMPLE_REPORT.tenant_id,
        period_year: 2026,
        period_month: 4,
        report_type: 'zp_vszp',
        file_path: '/reports/2026/04/zp_vszp.xml',
        file_format: 'xml',
        status: 'generated',
        deadline_date: '2026-05-03',
        institution: 'VsZP',
      }
      mockedApi.post.mockResolvedValue({ data: { ...SAMPLE_REPORT, ...payload } })

      const result = await createMonthlyReport(payload)

      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/monthly-reports', payload)
      expect(result.report_type).toBe('zp_vszp')
    })
  })

  describe('updateMonthlyReport', () => {
    it('calls PATCH /api/v1/monthly-reports/:id (not PUT)', async () => {
      const payload: MonthlyReportUpdate = {
        status: 'submitted',
        submitted_at: '2026-04-15T10:00:00Z',
      }
      mockedApi.patch.mockResolvedValue({
        data: { ...SAMPLE_REPORT, ...payload },
      })

      const result = await updateMonthlyReport(SAMPLE_REPORT.id, payload)

      expect(mockedApi.patch).toHaveBeenCalledWith(
        `/api/v1/monthly-reports/${SAMPLE_REPORT.id}`,
        payload,
      )
      expect(result.status).toBe('submitted')
      // Verify it does NOT call put
      expect(mockedApi.get).not.toHaveBeenCalled()
    })
  })

  describe('deleteMonthlyReport', () => {
    it('calls DELETE /api/v1/monthly-reports/:id', async () => {
      mockedApi.delete.mockResolvedValue({ data: undefined })

      await deleteMonthlyReport(SAMPLE_REPORT.id)

      expect(mockedApi.delete).toHaveBeenCalledWith(
        `/api/v1/monthly-reports/${SAMPLE_REPORT.id}`,
      )
    })
  })
})
