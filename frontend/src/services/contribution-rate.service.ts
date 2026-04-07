import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type {
  ContributionRateCreate,
  ContributionRateRead,
  ContributionRateUpdate,
} from '@/types/contribution-rate'

const BASE = '/api/v1/contribution-rates'

export async function listContributionRates(
  params?: PaginationParams,
): Promise<PaginatedResponse<ContributionRateRead>> {
  const response = await api.get<PaginatedResponse<ContributionRateRead>>(BASE, { params })
  return response.data
}

export async function getContributionRate(id: string): Promise<ContributionRateRead> {
  const response = await api.get<ContributionRateRead>(`${BASE}/${id}`)
  return response.data
}

export async function createContributionRate(
  data: ContributionRateCreate,
): Promise<ContributionRateRead> {
  const response = await api.post<ContributionRateRead>(BASE, data)
  return response.data
}

export async function updateContributionRate(
  id: string,
  data: ContributionRateUpdate,
): Promise<ContributionRateRead> {
  const response = await api.patch<ContributionRateRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteContributionRate(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
