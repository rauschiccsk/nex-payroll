import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type {
  PaymentOrderCreate,
  PaymentOrderRead,
  PaymentOrderUpdate,
  PaymentStatus,
  PaymentType,
} from '@/types/payment-order'

const BASE = '/api/v1/payment-orders'

export interface PaymentOrderListParams extends PaginationParams {
  tenant_id?: string
  payment_type?: PaymentType
  status?: PaymentStatus
  period_year?: number
  period_month?: number
}

export async function listPaymentOrders(
  params?: PaymentOrderListParams,
): Promise<PaginatedResponse<PaymentOrderRead>> {
  const response = await api.get<PaginatedResponse<PaymentOrderRead>>(BASE, { params })
  return response.data
}

export async function getPaymentOrder(id: string): Promise<PaymentOrderRead> {
  const response = await api.get<PaymentOrderRead>(`${BASE}/${id}`)
  return response.data
}

export async function createPaymentOrder(data: PaymentOrderCreate): Promise<PaymentOrderRead> {
  const response = await api.post<PaymentOrderRead>(BASE, data)
  return response.data
}

export async function updatePaymentOrder(
  id: string,
  data: PaymentOrderUpdate,
): Promise<PaymentOrderRead> {
  const response = await api.patch<PaymentOrderRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deletePaymentOrder(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
