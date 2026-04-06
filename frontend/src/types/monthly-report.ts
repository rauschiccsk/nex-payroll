// ---------------------------------------------------------------------------
// MonthlyReport types — matches backend app.schemas.monthly_report
// ---------------------------------------------------------------------------

export type ReportType =
  | 'sp_monthly'
  | 'zp_vszp'
  | 'zp_dovera'
  | 'zp_union'
  | 'tax_prehled';

export type ReportStatus = 'generated' | 'submitted' | 'accepted' | 'rejected';
export type FileFormat = 'xml' | 'pdf';

export interface MonthlyReportCreate {
  tenant_id: string;
  period_year: number;
  period_month: number;
  report_type: ReportType;
  file_path: string;
  file_format?: FileFormat;
  status?: ReportStatus;
  deadline_date: string;
  institution: string;
  submitted_at?: string | null;
  health_insurer_id?: string | null;
}

export interface MonthlyReportUpdate {
  file_path?: string | null;
  file_format?: FileFormat | null;
  status?: ReportStatus | null;
  deadline_date?: string | null;
  institution?: string | null;
  submitted_at?: string | null;
  health_insurer_id?: string | null;
}

export interface MonthlyReportRead {
  id: string;
  tenant_id: string;
  period_year: number;
  period_month: number;
  report_type: ReportType;
  file_path: string;
  file_format: FileFormat;
  status: ReportStatus;
  deadline_date: string;
  institution: string;
  submitted_at: string | null;
  health_insurer_id: string | null;
  created_at: string;
  updated_at: string;
}
