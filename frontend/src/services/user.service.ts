import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type { UserCreate, UserRead, UserUpdate } from '@/types/user'

const BASE = '/api/v1/users'

export async function listUsers(
  params?: PaginationParams,
): Promise<PaginatedResponse<UserRead>> {
  const response = await api.get<PaginatedResponse<UserRead>>(BASE, { params })
  return response.data
}

export async function getUser(id: string): Promise<UserRead> {
  const response = await api.get<UserRead>(`${BASE}/${id}`)
  return response.data
}

export async function createUser(data: UserCreate): Promise<UserRead> {
  const response = await api.post<UserRead>(BASE, data)
  return response.data
}

export async function updateUser(id: string, data: UserUpdate): Promise<UserRead> {
  const response = await api.patch<UserRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteUser(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
