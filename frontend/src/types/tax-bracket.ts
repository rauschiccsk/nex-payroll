// ---------------------------------------------------------------------------
// TaxBracket types — matches backend app.schemas.tax_bracket
// ---------------------------------------------------------------------------

export interface TaxBracketCreate {
  bracket_order: number;
  min_amount: number;
  max_amount?: number | null;
  rate_percent: number;
  nczd_annual: number;
  nczd_monthly: number;
  nczd_reduction_threshold: number;
  nczd_reduction_formula: string;
  valid_from: string;
  valid_to?: string | null;
}

export interface TaxBracketUpdate {
  bracket_order?: number | null;
  min_amount?: number | null;
  max_amount?: number | null;
  rate_percent?: number | null;
  nczd_annual?: number | null;
  nczd_monthly?: number | null;
  nczd_reduction_threshold?: number | null;
  nczd_reduction_formula?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface TaxBracketRead {
  id: string;
  bracket_order: number;
  min_amount: number;
  max_amount: number | null;
  rate_percent: number;
  nczd_annual: number;
  nczd_monthly: number;
  nczd_reduction_threshold: number;
  nczd_reduction_formula: string;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
}
