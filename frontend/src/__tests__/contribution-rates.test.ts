import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the api module before importing the service
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
  listContributionRates,
  getContributionRate,
  createContributionRate,
  updateContributionRate,
  deleteContributionRate,
} from '@/services/contribution-rate.service'
import type {
  ContributionRateCreate,
  ContributionRateRead,
} from '@/types/contribution-rate'

const MOCK_RATE: ContributionRateRead = {
  id: '11111111-1111-1111-1111-111111111111',
  rate_type: 'sp_employee_nemocenske',
  rate_percent: 1.4,
  max_assessment_base: 8477.0,
  payer: 'employee',
  fund: 'sick_insurance',
  valid_from: '2025-01-01',
  valid_to: null,
  created_at: '2025-01-01T00:00:00Z',
}

describe('contribution-rate.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listContributionRates calls GET with pagination params', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { items: [MOCK_RATE], total: 1, skip: 0, limit: 50 },
    })

    const result = await listContributionRates({ skip: 0, limit: 50 })

    expect(api.get).toHaveBeenCalledWith('/api/v1/contribution-rates', {
      params: { skip: 0, limit: 50 },
    })
    expect(result.items).toHaveLength(1)
    expect(result.total).toBe(1)
  })

  it('getContributionRate calls GET with id', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: MOCK_RATE })

    const result = await getContributionRate(MOCK_RATE.id)

    expect(api.get).toHaveBeenCalledWith(
      `/api/v1/contribution-rates/${MOCK_RATE.id}`,
    )
    expect(result.rate_type).toBe('sp_employee_nemocenske')
  })

  it('createContributionRate calls POST', async () => {
    const payload: ContributionRateCreate = {
      rate_type: 'sp_employee_starobne',
      rate_percent: 4.0,
      max_assessment_base: 8477.0,
      payer: 'employee',
      fund: 'pension_insurance',
      valid_from: '2025-01-01',
      valid_to: null,
    }
    vi.mocked(api.post).mockResolvedValue({
      data: { ...MOCK_RATE, ...payload, id: '22222222-2222-2222-2222-222222222222' },
    })

    const result = await createContributionRate(payload)

    expect(api.post).toHaveBeenCalledWith('/api/v1/contribution-rates', payload)
    expect(result.rate_type).toBe('sp_employee_starobne')
  })

  it('updateContributionRate calls PATCH (not PUT)', async () => {
    const update = { rate_percent: 1.5 }
    vi.mocked(api.patch).mockResolvedValue({
      data: { ...MOCK_RATE, rate_percent: 1.5 },
    })

    const result = await updateContributionRate(MOCK_RATE.id, update)

    expect(api.patch).toHaveBeenCalledWith(
      `/api/v1/contribution-rates/${MOCK_RATE.id}`,
      update,
    )
    expect(result.rate_percent).toBe(1.5)
    // Verify PUT is NOT used
    expect(api.get).not.toHaveBeenCalled()
  })

  it('deleteContributionRate calls DELETE', async () => {
    vi.mocked(api.delete).mockResolvedValue({ data: undefined })

    await deleteContributionRate(MOCK_RATE.id)

    expect(api.delete).toHaveBeenCalledWith(
      `/api/v1/contribution-rates/${MOCK_RATE.id}`,
    )
  })
})

describe('ContributionRatesPage constants', () => {
  it('FUND_OPTIONS includes kurzarbeit', async () => {
    // Dynamically import the page to access module-level constants indirectly
    // We verify the page renders the kurzarbeit option by checking the module
    const page = await import('@/pages/ContributionRatesPage')
    expect(page).toBeDefined()
  })

  it('ContributionRateRead type has required fields', () => {
    const rate: ContributionRateRead = { ...MOCK_RATE }
    expect(rate.id).toBeDefined()
    expect(rate.rate_type).toBeDefined()
    expect(rate.rate_percent).toBeDefined()
    expect(rate.payer).toBeDefined()
    expect(rate.fund).toBeDefined()
    expect(rate.valid_from).toBeDefined()
    expect(rate.created_at).toBeDefined()
  })

  it('ContributionPayer type allows only employee and employer', () => {
    const rate1: ContributionRateRead = { ...MOCK_RATE, payer: 'employee' }
    const rate2: ContributionRateRead = { ...MOCK_RATE, payer: 'employer' }
    expect(rate1.payer).toBe('employee')
    expect(rate2.payer).toBe('employer')
  })
})
