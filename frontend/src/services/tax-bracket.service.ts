import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type {
  TaxBracketCreate,
  TaxBracketRead,
  TaxBracketUpdate,
} from '@/types/tax-bracket'

const BASE = '/api/v1/tax-brackets'

export async function listTaxBrackets(
  params?: PaginationParams,
): Promise<PaginatedResponse<TaxBracketRead>> {
  const response = await api.get<PaginatedResponse<TaxBracketRead>>(BASE, { params })
  return response.data
}

export async function getTaxBracket(id: string): Promise<TaxBracketRead> {
  const response = await api.get<TaxBracketRead>(`${BASE}/${id}`)
  return response.data
}

export async function createTaxBracket(data: TaxBracketCreate): Promise<TaxBracketRead> {
  const response = await api.post<TaxBracketRead>(BASE, data)
  return response.data
}

export async function updateTaxBracket(
  id: string,
  data: TaxBracketUpdate,
): Promise<TaxBracketRead> {
  const response = await api.patch<TaxBracketRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteTaxBracket(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
