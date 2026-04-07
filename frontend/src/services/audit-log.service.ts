import api from './api'
import type { PaginatedResponse } from '@/types/common'
import type { AuditLogRead } from '@/types/audit-log'

const BASE = '/api/v1/audit-logs'

export interface AuditLogFilterParams {
  skip?: number
  limit?: number
  tenant_id?: string
  entity_type?: string
  entity_id?: string
  user_id?: string
  action?: string
}

export async function listAuditLogs(
  params?: AuditLogFilterParams,
): Promise<PaginatedResponse<AuditLogRead>> {
  const response = await api.get<PaginatedResponse<AuditLogRead>>(BASE, { params })
  return response.data
}

export async function getAuditLog(id: string): Promise<AuditLogRead> {
  const response = await api.get<AuditLogRead>(`${BASE}/${id}`)
  return response.data
}
