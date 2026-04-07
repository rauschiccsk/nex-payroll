import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type {
  MonthlyReportCreate,
  MonthlyReportRead,
  MonthlyReportUpdate,
  ReportStatus,
  ReportType,
} from '@/types/monthly-report'

const BASE = '/api/v1/monthly-reports'

export interface MonthlyReportListParams extends PaginationParams {
  tenant_id?: string
  report_type?: ReportType
  status?: ReportStatus
  period_year?: number
  period_month?: number
}

export async function listMonthlyReports(
  params?: MonthlyReportListParams,
): Promise<PaginatedResponse<MonthlyReportRead>> {
  const response = await api.get<PaginatedResponse<MonthlyReportRead>>(BASE, { params })
  return response.data
}

export async function getMonthlyReport(id: string): Promise<MonthlyReportRead> {
  const response = await api.get<MonthlyReportRead>(`${BASE}/${id}`)
  return response.data
}

export async function createMonthlyReport(data: MonthlyReportCreate): Promise<MonthlyReportRead> {
  const response = await api.post<MonthlyReportRead>(BASE, data)
  return response.data
}

export async function updateMonthlyReport(
  id: string,
  data: MonthlyReportUpdate,
): Promise<MonthlyReportRead> {
  const response = await api.patch<MonthlyReportRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteMonthlyReport(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
