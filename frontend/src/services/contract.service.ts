import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type { ContractCreate, ContractRead, ContractUpdate } from '@/types/contract'

const BASE = '/api/v1/contracts'

export async function listContracts(
  params?: PaginationParams & { employee_id?: string },
): Promise<PaginatedResponse<ContractRead>> {
  const response = await api.get<PaginatedResponse<ContractRead>>(BASE, { params })
  return response.data
}

export async function getContract(id: string): Promise<ContractRead> {
  const response = await api.get<ContractRead>(`${BASE}/${id}`)
  return response.data
}

export async function createContract(data: ContractCreate): Promise<ContractRead> {
  const response = await api.post<ContractRead>(BASE, data)
  return response.data
}

export async function updateContract(id: string, data: ContractUpdate): Promise<ContractRead> {
  const response = await api.patch<ContractRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteContract(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
