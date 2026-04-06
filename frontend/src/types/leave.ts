// ---------------------------------------------------------------------------
// Leave types — matches backend app.schemas.leave
// ---------------------------------------------------------------------------

export type LeaveType =
  | 'annual'
  | 'sick_employer'
  | 'sick_sp'
  | 'ocr'
  | 'maternity'
  | 'parental'
  | 'unpaid'
  | 'obstacle';

export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled';

export interface LeaveCreate {
  tenant_id: string;
  employee_id: string;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  business_days: number;
  status?: LeaveStatus;
  note?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
}

export interface LeaveUpdate {
  leave_type?: LeaveType | null;
  start_date?: string | null;
  end_date?: string | null;
  business_days?: number | null;
  status?: LeaveStatus | null;
  note?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
}

export interface LeaveRead {
  id: string;
  tenant_id: string;
  employee_id: string;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  business_days: number;
  status: LeaveStatus;
  note: string | null;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}
