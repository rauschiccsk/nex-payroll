// ---------------------------------------------------------------------------
// ContributionRate types — matches backend app.schemas.contribution_rate
// ---------------------------------------------------------------------------

export type ContributionPayer = 'employee' | 'employer';

export interface ContributionRateCreate {
  rate_type: string;
  rate_percent: number;
  max_assessment_base?: number | null;
  payer: ContributionPayer;
  fund: string;
  valid_from: string;
  valid_to?: string | null;
}

export interface ContributionRateUpdate {
  rate_type?: string | null;
  rate_percent?: number | null;
  max_assessment_base?: number | null;
  payer?: ContributionPayer | null;
  fund?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface ContributionRateRead {
  id: string;
  rate_type: string;
  rate_percent: number;
  max_assessment_base: number | null;
  payer: ContributionPayer;
  fund: string;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
}
