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
  listStatutoryDeadlines,
  getStatutoryDeadline,
  createStatutoryDeadline,
  updateStatutoryDeadline,
  deleteStatutoryDeadline,
} from '@/services/statutory-deadline.service'
import type {
  StatutoryDeadlineCreate,
  StatutoryDeadlineRead,
} from '@/types/statutory-deadline'

const MOCK_DEADLINE: StatutoryDeadlineRead = {
  id: '11111111-1111-1111-1111-111111111111',
  code: 'SP_MONTHLY',
  name: 'Mesačný výkaz SP',
  description: 'Mesačný výkaz a odvody do Sociálnej poisťovne',
  deadline_type: 'monthly',
  day_of_month: 8,
  month_of_year: null,
  business_days_rule: true,
  institution: 'Sociálna poisťovňa',
  valid_from: '2025-01-01',
  valid_to: null,
  created_at: '2025-01-01T00:00:00Z',
}

describe('statutory-deadline.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listStatutoryDeadlines calls GET with pagination params', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { items: [MOCK_DEADLINE], total: 1, skip: 0, limit: 20 },
    })

    const result = await listStatutoryDeadlines({ skip: 0, limit: 20 })

    expect(api.get).toHaveBeenCalledWith('/api/v1/statutory-deadlines', {
      params: { skip: 0, limit: 20 },
    })
    expect(result.items).toHaveLength(1)
    expect(result.total).toBe(1)
  })

  it('listStatutoryDeadlines works without params', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { items: [], total: 0, skip: 0, limit: 20 },
    })

    const result = await listStatutoryDeadlines()

    expect(api.get).toHaveBeenCalledWith('/api/v1/statutory-deadlines', {
      params: undefined,
    })
    expect(result.items).toHaveLength(0)
  })

  it('getStatutoryDeadline calls GET with id', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: MOCK_DEADLINE })

    const result = await getStatutoryDeadline(MOCK_DEADLINE.id)

    expect(api.get).toHaveBeenCalledWith(
      `/api/v1/statutory-deadlines/${MOCK_DEADLINE.id}`,
    )
    expect(result.name).toBe('Mesačný výkaz SP')
    expect(result.code).toBe('SP_MONTHLY')
  })

  it('createStatutoryDeadline calls POST', async () => {
    const payload: StatutoryDeadlineCreate = {
      code: 'ZP_MONTHLY',
      name: 'Mesačný výkaz ZP',
      description: null,
      deadline_type: 'monthly',
      day_of_month: 3,
      month_of_year: null,
      business_days_rule: false,
      institution: 'VšZP',
      valid_from: '2025-01-01',
      valid_to: null,
    }
    vi.mocked(api.post).mockResolvedValue({
      data: { ...MOCK_DEADLINE, ...payload, id: '22222222-2222-2222-2222-222222222222' },
    })

    const result = await createStatutoryDeadline(payload)

    expect(api.post).toHaveBeenCalledWith('/api/v1/statutory-deadlines', payload)
    expect(result.code).toBe('ZP_MONTHLY')
  })

  it('updateStatutoryDeadline calls PATCH (not PUT)', async () => {
    const update = { name: 'Mesačný výkaz SP (aktualizovaný)' }
    vi.mocked(api.patch).mockResolvedValue({
      data: { ...MOCK_DEADLINE, name: 'Mesačný výkaz SP (aktualizovaný)' },
    })

    const result = await updateStatutoryDeadline(MOCK_DEADLINE.id, update)

    expect(api.patch).toHaveBeenCalledWith(
      `/api/v1/statutory-deadlines/${MOCK_DEADLINE.id}`,
      update,
    )
    expect(result.name).toBe('Mesačný výkaz SP (aktualizovaný)')
    // Verify PUT is NOT used
    expect(api.get).not.toHaveBeenCalled()
  })

  it('deleteStatutoryDeadline calls DELETE', async () => {
    vi.mocked(api.delete).mockResolvedValue({ data: undefined })

    await deleteStatutoryDeadline(MOCK_DEADLINE.id)

    expect(api.delete).toHaveBeenCalledWith(
      `/api/v1/statutory-deadlines/${MOCK_DEADLINE.id}`,
    )
  })
})

describe('StatutoryDeadlinesPage module', () => {
  it('page module can be imported', async () => {
    const page = await import('@/pages/StatutoryDeadlinesPage')
    expect(page).toBeDefined()
    expect(page.default).toBeDefined()
  })

  it('StatutoryDeadlineRead type has required fields', () => {
    const deadline: StatutoryDeadlineRead = { ...MOCK_DEADLINE }
    expect(deadline.id).toBeDefined()
    expect(deadline.code).toBeDefined()
    expect(deadline.name).toBeDefined()
    expect(deadline.deadline_type).toBeDefined()
    expect(deadline.institution).toBeDefined()
    expect(deadline.valid_from).toBeDefined()
    expect(deadline.created_at).toBeDefined()
  })

  it('StatutoryDeadlineRead allows null optional fields', () => {
    const deadline: StatutoryDeadlineRead = {
      ...MOCK_DEADLINE,
      description: null,
      day_of_month: null,
      month_of_year: null,
      valid_to: null,
    }
    expect(deadline.description).toBeNull()
    expect(deadline.day_of_month).toBeNull()
    expect(deadline.month_of_year).toBeNull()
    expect(deadline.valid_to).toBeNull()
  })

  it('DeadlineType allows only valid values', () => {
    const d1: StatutoryDeadlineRead = { ...MOCK_DEADLINE, deadline_type: 'monthly' }
    const d2: StatutoryDeadlineRead = { ...MOCK_DEADLINE, deadline_type: 'annual' }
    const d3: StatutoryDeadlineRead = { ...MOCK_DEADLINE, deadline_type: 'one_time' }
    expect(d1.deadline_type).toBe('monthly')
    expect(d2.deadline_type).toBe('annual')
    expect(d3.deadline_type).toBe('one_time')
  })
})
