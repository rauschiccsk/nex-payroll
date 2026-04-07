import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type {
  HealthInsurerCreate,
  HealthInsurerRead,
  HealthInsurerUpdate,
} from '@/types/health-insurer'

const BASE = '/api/v1/health-insurers'

export async function listHealthInsurers(
  params?: PaginationParams,
): Promise<PaginatedResponse<HealthInsurerRead>> {
  const response = await api.get<PaginatedResponse<HealthInsurerRead>>(BASE, { params })
  return response.data
}

export async function getHealthInsurer(id: string): Promise<HealthInsurerRead> {
  const response = await api.get<HealthInsurerRead>(`${BASE}/${id}`)
  return response.data
}

export async function createHealthInsurer(
  data: HealthInsurerCreate,
): Promise<HealthInsurerRead> {
  const response = await api.post<HealthInsurerRead>(BASE, data)
  return response.data
}

export async function updateHealthInsurer(
  id: string,
  data: HealthInsurerUpdate,
): Promise<HealthInsurerRead> {
  const response = await api.patch<HealthInsurerRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteHealthInsurer(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
