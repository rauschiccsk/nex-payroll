// ---------------------------------------------------------------------------
// StatutoryDeadline types — matches backend app.schemas.statutory_deadline
// ---------------------------------------------------------------------------

export type DeadlineType =
  | 'sp_monthly'
  | 'zp_monthly'
  | 'tax_advance'
  | 'tax_reconciliation'
  | 'sp_annual'
  | 'zp_annual';

export interface StatutoryDeadlineCreate {
  deadline_type: DeadlineType;
  institution: string;
  day_of_month: number;
  description: string;
  valid_from: string;
  valid_to?: string | null;
  is_active?: boolean;
}

export interface StatutoryDeadlineUpdate {
  deadline_type?: DeadlineType | null;
  institution?: string | null;
  day_of_month?: number | null;
  description?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
  is_active?: boolean | null;
}

export interface StatutoryDeadlineRead {
  id: string;
  deadline_type: DeadlineType;
  institution: string;
  day_of_month: number;
  description: string;
  valid_from: string;
  valid_to: string | null;
  is_active: boolean;
  created_at: string;
}
