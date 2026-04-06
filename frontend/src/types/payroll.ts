// ---------------------------------------------------------------------------
// Payroll types — matches backend app.schemas.payroll
// ---------------------------------------------------------------------------

export type PayrollStatus = 'draft' | 'calculated' | 'approved' | 'paid';
export type LedgerSyncStatus = 'pending' | 'synced' | 'error';

export interface PayrollCreate {
  tenant_id: string;
  employee_id: string;
  contract_id: string;
  period_year: number;
  period_month: number;
  status?: PayrollStatus;
  // Gross wage components
  base_wage: number;
  overtime_hours?: number;
  overtime_amount?: number;
  bonus_amount?: number;
  supplement_amount?: number;
  gross_wage: number;
  // SP employee contributions
  sp_assessment_base: number;
  sp_nemocenske: number;
  sp_starobne: number;
  sp_invalidne: number;
  sp_nezamestnanost: number;
  sp_employee_total: number;
  // ZP employee contribution
  zp_assessment_base: number;
  zp_employee: number;
  // Tax calculation
  partial_tax_base: number;
  nczd_applied: number;
  tax_base: number;
  tax_advance: number;
  child_bonus?: number;
  tax_after_bonus: number;
  // Net wage
  net_wage: number;
  // SP employer contributions
  sp_employer_nemocenske: number;
  sp_employer_starobne: number;
  sp_employer_invalidne: number;
  sp_employer_nezamestnanost: number;
  sp_employer_garancne: number;
  sp_employer_rezervny: number;
  sp_employer_kurzarbeit: number;
  sp_employer_urazove: number;
  sp_employer_total: number;
  zp_employer: number;
  total_employer_cost: number;
  // Pillar 2
  pillar2_amount?: number;
}

export interface PayrollUpdate {
  status?: PayrollStatus | null;
  // Gross wage components
  base_wage?: number | null;
  overtime_hours?: number | null;
  overtime_amount?: number | null;
  bonus_amount?: number | null;
  supplement_amount?: number | null;
  gross_wage?: number | null;
  // SP employee contributions
  sp_assessment_base?: number | null;
  sp_nemocenske?: number | null;
  sp_starobne?: number | null;
  sp_invalidne?: number | null;
  sp_nezamestnanost?: number | null;
  sp_employee_total?: number | null;
  // ZP employee contribution
  zp_assessment_base?: number | null;
  zp_employee?: number | null;
  // Tax calculation
  partial_tax_base?: number | null;
  nczd_applied?: number | null;
  tax_base?: number | null;
  tax_advance?: number | null;
  child_bonus?: number | null;
  tax_after_bonus?: number | null;
  // Net wage
  net_wage?: number | null;
  // SP employer contributions
  sp_employer_nemocenske?: number | null;
  sp_employer_starobne?: number | null;
  sp_employer_invalidne?: number | null;
  sp_employer_nezamestnanost?: number | null;
  sp_employer_garancne?: number | null;
  sp_employer_rezervny?: number | null;
  sp_employer_kurzarbeit?: number | null;
  sp_employer_urazove?: number | null;
  sp_employer_total?: number | null;
  zp_employer?: number | null;
  total_employer_cost?: number | null;
  // Pillar 2
  pillar2_amount?: number | null;
  // AI validation
  ai_validation_result?: Record<string, unknown> | null;
  // Ledger sync
  ledger_sync_status?: LedgerSyncStatus | null;
  // Approval metadata
  calculated_at?: string | null;
  approved_at?: string | null;
  approved_by?: string | null;
}

export interface PayrollRead {
  id: string;
  tenant_id: string;
  employee_id: string;
  contract_id: string;
  period_year: number;
  period_month: number;
  status: PayrollStatus;
  // Gross wage components
  base_wage: number;
  overtime_hours: number;
  overtime_amount: number;
  bonus_amount: number;
  supplement_amount: number;
  gross_wage: number;
  // SP employee contributions
  sp_assessment_base: number;
  sp_nemocenske: number;
  sp_starobne: number;
  sp_invalidne: number;
  sp_nezamestnanost: number;
  sp_employee_total: number;
  // ZP employee contribution
  zp_assessment_base: number;
  zp_employee: number;
  // Tax calculation
  partial_tax_base: number;
  nczd_applied: number;
  tax_base: number;
  tax_advance: number;
  child_bonus: number;
  tax_after_bonus: number;
  // Net wage
  net_wage: number;
  // SP employer contributions
  sp_employer_nemocenske: number;
  sp_employer_starobne: number;
  sp_employer_invalidne: number;
  sp_employer_nezamestnanost: number;
  sp_employer_garancne: number;
  sp_employer_rezervny: number;
  sp_employer_kurzarbeit: number;
  sp_employer_urazove: number;
  sp_employer_total: number;
  zp_employer: number;
  total_employer_cost: number;
  // Pillar 2
  pillar2_amount: number;
  // AI validation
  ai_validation_result: Record<string, unknown> | null;
  // Ledger sync
  ledger_sync_status: LedgerSyncStatus | null;
  // Approval metadata
  calculated_at: string | null;
  approved_at: string | null;
  approved_by: string | null;
  // Timestamps
  created_at: string;
  updated_at: string;
}
