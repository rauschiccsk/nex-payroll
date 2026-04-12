// ---------------------------------------------------------------------------
// PaySlip types — matches backend app.schemas.pay_slip
// ---------------------------------------------------------------------------

export interface PaySlipCreate {
  payroll_id: string;
  employee_id: string;
  period_year: number;
  period_month: number;
  pdf_path: string;
  file_size_bytes?: number | null;
}

export interface PaySlipUpdate {
  pdf_path?: string | null;
  file_size_bytes?: number | null;
  downloaded_at?: string | null;
}

export interface PaySlipRead {
  id: string;
  tenant_id: string;
  payroll_id: string;
  employee_id: string;
  period_year: number;
  period_month: number;
  pdf_path: string;
  file_size_bytes: number | null;
  generated_at: string;
  downloaded_at: string | null;
  created_at: string;
  updated_at: string;
}
