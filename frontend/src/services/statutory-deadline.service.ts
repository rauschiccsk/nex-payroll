import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type {
  StatutoryDeadlineCreate,
  StatutoryDeadlineRead,
  StatutoryDeadlineUpdate,
} from '@/types/statutory-deadline'

const BASE = '/api/v1/statutory-deadlines'

export async function listStatutoryDeadlines(
  params?: PaginationParams,
): Promise<PaginatedResponse<StatutoryDeadlineRead>> {
  const response = await api.get<PaginatedResponse<StatutoryDeadlineRead>>(BASE, { params })
  return response.data
}

export async function getStatutoryDeadline(id: string): Promise<StatutoryDeadlineRead> {
  const response = await api.get<StatutoryDeadlineRead>(`${BASE}/${id}`)
  return response.data
}

export async function createStatutoryDeadline(
  data: StatutoryDeadlineCreate,
): Promise<StatutoryDeadlineRead> {
  const response = await api.post<StatutoryDeadlineRead>(BASE, data)
  return response.data
}

export async function updateStatutoryDeadline(
  id: string,
  data: StatutoryDeadlineUpdate,
): Promise<StatutoryDeadlineRead> {
  const response = await api.patch<StatutoryDeadlineRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteStatutoryDeadline(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
