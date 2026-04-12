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
  listHealthInsurers,
  getHealthInsurer,
  createHealthInsurer,
  updateHealthInsurer,
  deleteHealthInsurer,
} from '@/services/health-insurer.service'
import type {
  HealthInsurerCreate,
  HealthInsurerRead,
} from '@/types/health-insurer'

const MOCK_INSURER: HealthInsurerRead = {
  id: '11111111-1111-1111-1111-111111111111',
  code: '24',
  name: 'Dovera ZP',
  iban: 'SK1234567890123456789012',
  bic: 'SUBASKBX',
  is_active: true,
  created_at: '2025-01-01T00:00:00Z',
}

describe('health-insurer.service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listHealthInsurers calls GET with pagination params', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { items: [MOCK_INSURER], total: 1, skip: 0, limit: 20 },
    })

    const result = await listHealthInsurers({ skip: 0, limit: 20 })

    expect(api.get).toHaveBeenCalledWith('/api/v1/health-insurers', {
      params: { skip: 0, limit: 20 },
    })
    expect(result.items).toHaveLength(1)
    expect(result.total).toBe(1)
  })

  it('listHealthInsurers works without params', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { items: [], total: 0, skip: 0, limit: 20 },
    })

    const result = await listHealthInsurers()

    expect(api.get).toHaveBeenCalledWith('/api/v1/health-insurers', {
      params: undefined,
    })
    expect(result.items).toHaveLength(0)
  })

  it('getHealthInsurer calls GET with id', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: MOCK_INSURER })

    const result = await getHealthInsurer(MOCK_INSURER.id)

    expect(api.get).toHaveBeenCalledWith(
      `/api/v1/health-insurers/${MOCK_INSURER.id}`,
    )
    expect(result.name).toBe('Dovera ZP')
    expect(result.code).toBe('24')
  })

  it('createHealthInsurer calls POST', async () => {
    const payload: HealthInsurerCreate = {
      code: '25',
      name: 'VsZP',
      iban: 'SK9876543210987654321098',
      bic: null,
      is_active: true,
    }
    vi.mocked(api.post).mockResolvedValue({
      data: { ...MOCK_INSURER, ...payload, id: '22222222-2222-2222-2222-222222222222' },
    })

    const result = await createHealthInsurer(payload)

    expect(api.post).toHaveBeenCalledWith('/api/v1/health-insurers', payload)
    expect(result.name).toBe('VsZP')
  })

  it('updateHealthInsurer calls PATCH (not PUT)', async () => {
    const update = { name: 'Dovera zdravotna poistovna' }
    vi.mocked(api.patch).mockResolvedValue({
      data: { ...MOCK_INSURER, name: 'Dovera zdravotna poistovna' },
    })

    const result = await updateHealthInsurer(MOCK_INSURER.id, update)

    expect(api.patch).toHaveBeenCalledWith(
      `/api/v1/health-insurers/${MOCK_INSURER.id}`,
      update,
    )
    expect(result.name).toBe('Dovera zdravotna poistovna')
    // Verify PUT is NOT used
    expect(api.get).not.toHaveBeenCalled()
  })

  it('deleteHealthInsurer calls DELETE', async () => {
    vi.mocked(api.delete).mockResolvedValue({ data: undefined })

    await deleteHealthInsurer(MOCK_INSURER.id)

    expect(api.delete).toHaveBeenCalledWith(
      `/api/v1/health-insurers/${MOCK_INSURER.id}`,
    )
  })
})

describe('HealthInsurersPage module', () => {
  it('page module can be imported', async () => {
    const page = await import('@/pages/HealthInsurersPage')
    expect(page).toBeDefined()
    expect(page.default).toBeDefined()
  })

  it('HealthInsurerRead type has required fields', () => {
    const insurer: HealthInsurerRead = { ...MOCK_INSURER }
    expect(insurer.id).toBeDefined()
    expect(insurer.code).toBeDefined()
    expect(insurer.name).toBeDefined()
    expect(insurer.iban).toBeDefined()
    expect(insurer.is_active).toBe(true)
    expect(insurer.created_at).toBeDefined()
  })

  it('HealthInsurerRead allows null bic', () => {
    const insurer: HealthInsurerRead = { ...MOCK_INSURER, bic: null }
    expect(insurer.bic).toBeNull()
  })
})
