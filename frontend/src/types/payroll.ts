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
  base_wage: string;
  overtime_hours?: string;
  overtime_amount?: string;
  bonus_amount?: string;
  supplement_amount?: string;
  gross_wage: string;
  // SP employee contributions
  sp_assessment_base: string;
  sp_nemocenske: string;
  sp_starobne: string;
  sp_invalidne: string;
  sp_nezamestnanost: string;
  sp_employee_total: string;
  // ZP employee contribution
  zp_assessment_base: string;
  zp_employee: string;
  // Tax calculation
  partial_tax_base: string;
  nczd_applied: string;
  tax_base: string;
  tax_advance: string;
  child_bonus?: string;
  tax_after_bonus: string;
  // Net wage
  net_wage: string;
  // SP employer contributions
  sp_employer_nemocenske: string;
  sp_employer_starobne: string;
  sp_employer_invalidne: string;
  sp_employer_nezamestnanost: string;
  sp_employer_garancne: string;
  sp_employer_rezervny: string;
  sp_employer_kurzarbeit: string;
  sp_employer_urazove: string;
  sp_employer_total: string;
  zp_employer: string;
  total_employer_cost: string;
  // Pillar 2
  pillar2_amount?: string;
}

export interface PayrollUpdate {
  status?: PayrollStatus | null;
  // Gross wage components
  base_wage?: string | null;
  overtime_hours?: string | null;
  overtime_amount?: string | null;
  bonus_amount?: string | null;
  supplement_amount?: string | null;
  gross_wage?: string | null;
  // SP employee contributions
  sp_assessment_base?: string | null;
  sp_nemocenske?: string | null;
  sp_starobne?: string | null;
  sp_invalidne?: string | null;
  sp_nezamestnanost?: string | null;
  sp_employee_total?: string | null;
  // ZP employee contribution
  zp_assessment_base?: string | null;
  zp_employee?: string | null;
  // Tax calculation
  partial_tax_base?: string | null;
  nczd_applied?: string | null;
  tax_base?: string | null;
  tax_advance?: string | null;
  child_bonus?: string | null;
  tax_after_bonus?: string | null;
  // Net wage
  net_wage?: string | null;
  // SP employer contributions
  sp_employer_nemocenske?: string | null;
  sp_employer_starobne?: string | null;
  sp_employer_invalidne?: string | null;
  sp_employer_nezamestnanost?: string | null;
  sp_employer_garancne?: string | null;
  sp_employer_rezervny?: string | null;
  sp_employer_kurzarbeit?: string | null;
  sp_employer_urazove?: string | null;
  sp_employer_total?: string | null;
  zp_employer?: string | null;
  total_employer_cost?: string | null;
  // Pillar 2
  pillar2_amount?: string | null;
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
  base_wage: string;
  overtime_hours: string;
  overtime_amount: string;
  bonus_amount: string;
  supplement_amount: string;
  gross_wage: string;
  // SP employee contributions
  sp_assessment_base: string;
  sp_nemocenske: string;
  sp_starobne: string;
  sp_invalidne: string;
  sp_nezamestnanost: string;
  sp_employee_total: string;
  // ZP employee contribution
  zp_assessment_base: string;
  zp_employee: string;
  // Tax calculation
  partial_tax_base: string;
  nczd_applied: string;
  tax_base: string;
  tax_advance: string;
  child_bonus: string;
  tax_after_bonus: string;
  // Net wage
  net_wage: string;
  // SP employer contributions
  sp_employer_nemocenske: string;
  sp_employer_starobne: string;
  sp_employer_invalidne: string;
  sp_employer_nezamestnanost: string;
  sp_employer_garancne: string;
  sp_employer_rezervny: string;
  sp_employer_kurzarbeit: string;
  sp_employer_urazove: string;
  sp_employer_total: string;
  zp_employer: string;
  total_employer_cost: string;
  // Pillar 2
  pillar2_amount: string;
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
