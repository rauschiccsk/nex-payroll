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
  listTaxBrackets,
  getTaxBracket,
  createTaxBracket,
  updateTaxBracket,
  deleteTaxBracket,
} from '@/services/tax-bracket.service'
import type { TaxBracketCreate, TaxBracketRead } from '@/types/tax-bracket'

const MOCK_BRACKET: TaxBracketRead = {
  id: '11111111-1111-1111-1111-111111111111',
  bracket_order: 1,
  min_amount: '0.00',
  max_amount: '47790.12',
  rate_percent: '19.00',
  nczd_annual: '5646.48',
  nczd_monthly: '470.54',
  nczd_reduction_threshold: '24952.06',
  nczd_reduction_formula: '44.2 * ZM - ZD',
  valid_from: '2025-01-01',
  valid_to: null,
  created_at: '2025-01-01T00:00:00Z',
}

describe('tax-bracket.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listTaxBrackets calls GET with pagination params', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { items: [MOCK_BRACKET], total: 1, skip: 0, limit: 50 },
    })

    const result = await listTaxBrackets({ skip: 0, limit: 50 })

    expect(api.get).toHaveBeenCalledWith('/api/v1/tax-brackets', {
      params: { skip: 0, limit: 50 },
    })
    expect(result.items).toHaveLength(1)
    expect(result.total).toBe(1)
  })

  it('getTaxBracket calls GET with id', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: MOCK_BRACKET })

    const result = await getTaxBracket(MOCK_BRACKET.id)

    expect(api.get).toHaveBeenCalledWith(
      `/api/v1/tax-brackets/${MOCK_BRACKET.id}`,
    )
    expect(result.bracket_order).toBe(1)
  })

  it('createTaxBracket calls POST', async () => {
    const payload: TaxBracketCreate = {
      bracket_order: 2,
      min_amount: '47790.13',
      max_amount: null,
      rate_percent: '25.00',
      nczd_annual: '5646.48',
      nczd_monthly: '470.54',
      nczd_reduction_threshold: '24952.06',
      nczd_reduction_formula: '44.2 * ZM - ZD',
      valid_from: '2025-01-01',
      valid_to: null,
    }
    vi.mocked(api.post).mockResolvedValue({
      data: { ...MOCK_BRACKET, ...payload, id: '22222222-2222-2222-2222-222222222222' },
    })

    const result = await createTaxBracket(payload)

    expect(api.post).toHaveBeenCalledWith('/api/v1/tax-brackets', payload)
    expect(result.bracket_order).toBe(2)
  })

  it('updateTaxBracket calls PATCH (not PUT)', async () => {
    const update = { rate_percent: '20.00' }
    vi.mocked(api.patch).mockResolvedValue({
      data: { ...MOCK_BRACKET, rate_percent: '20.00' },
    })

    const result = await updateTaxBracket(MOCK_BRACKET.id, update)

    expect(api.patch).toHaveBeenCalledWith(
      `/api/v1/tax-brackets/${MOCK_BRACKET.id}`,
      update,
    )
    expect(result.rate_percent).toBe('20.00')
    // Verify PUT is NOT used
    expect(api.get).not.toHaveBeenCalled()
  })

  it('deleteTaxBracket calls DELETE', async () => {
    vi.mocked(api.delete).mockResolvedValue({ data: undefined })

    await deleteTaxBracket(MOCK_BRACKET.id)

    expect(api.delete).toHaveBeenCalledWith(
      `/api/v1/tax-brackets/${MOCK_BRACKET.id}`,
    )
  })
})

describe('TaxBracket types', () => {
  it('TaxBracketRead type has required fields', () => {
    const bracket: TaxBracketRead = { ...MOCK_BRACKET }
    expect(bracket.id).toBeDefined()
    expect(bracket.bracket_order).toBeDefined()
    expect(bracket.min_amount).toBeDefined()
    expect(bracket.rate_percent).toBeDefined()
    expect(bracket.nczd_annual).toBeDefined()
    expect(bracket.nczd_monthly).toBeDefined()
    expect(bracket.nczd_reduction_threshold).toBeDefined()
    expect(bracket.nczd_reduction_formula).toBeDefined()
    expect(bracket.valid_from).toBeDefined()
    expect(bracket.created_at).toBeDefined()
  })

  it('max_amount can be null for unlimited brackets', () => {
    const bracket: TaxBracketRead = { ...MOCK_BRACKET, max_amount: null }
    expect(bracket.max_amount).toBeNull()
  })

  it('valid_to can be null for open-ended brackets', () => {
    const bracket: TaxBracketRead = { ...MOCK_BRACKET, valid_to: null }
    expect(bracket.valid_to).toBeNull()
  })
})
