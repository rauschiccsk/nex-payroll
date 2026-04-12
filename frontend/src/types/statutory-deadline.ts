// ---------------------------------------------------------------------------
// StatutoryDeadline types — matches backend app.schemas.statutory_deadline
// ---------------------------------------------------------------------------

export type DeadlineType = 'monthly' | 'annual' | 'one_time';

export interface StatutoryDeadlineCreate {
  code: string;
  name: string;
  description?: string | null;
  deadline_type: DeadlineType;
  day_of_month?: number | null;
  month_of_year?: number | null;
  business_days_rule: boolean;
  institution: string;
  valid_from: string;
  valid_to?: string | null;
}

export interface StatutoryDeadlineUpdate {
  code?: string | null;
  name?: string | null;
  description?: string | null;
  deadline_type?: DeadlineType | null;
  day_of_month?: number | null;
  month_of_year?: number | null;
  business_days_rule?: boolean | null;
  institution?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface StatutoryDeadlineRead {
  id: string;
  code: string;
  name: string;
  description: string | null;
  deadline_type: DeadlineType;
  day_of_month: number | null;
  month_of_year: number | null;
  business_days_rule: boolean;
  institution: string;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
}
