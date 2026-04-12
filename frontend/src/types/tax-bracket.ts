// ---------------------------------------------------------------------------
// TaxBracket types — matches backend app.schemas.tax_bracket
// ---------------------------------------------------------------------------

export interface TaxBracketCreate {
  bracket_order: number;
  min_amount: string;
  max_amount?: string | null;
  rate_percent: string;
  nczd_annual: string;
  nczd_monthly: string;
  nczd_reduction_threshold: string;
  nczd_reduction_formula: string;
  valid_from: string;
  valid_to?: string | null;
}

export interface TaxBracketUpdate {
  bracket_order?: number | null;
  min_amount?: string | null;
  max_amount?: string | null;
  rate_percent?: string | null;
  nczd_annual?: string | null;
  nczd_monthly?: string | null;
  nczd_reduction_threshold?: string | null;
  nczd_reduction_formula?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface TaxBracketRead {
  id: string;
  bracket_order: number;
  min_amount: string;
  max_amount: string | null;
  rate_percent: string;
  nczd_annual: string;
  nczd_monthly: string;
  nczd_reduction_threshold: string;
  nczd_reduction_formula: string;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
}
