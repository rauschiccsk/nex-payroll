// ---------------------------------------------------------------------------
// Contract types — matches backend app.schemas.contract
// ---------------------------------------------------------------------------

export type ContractType =
  | 'permanent'
  | 'fixed_term'
  | 'agreement_work'
  | 'agreement_activity';

export type WageType = 'monthly' | 'hourly';

export interface ContractCreate {
  tenant_id: string;
  employee_id: string;
  contract_number: string;
  contract_type: ContractType;
  job_title: string;
  wage_type: WageType;
  base_wage: number;
  hours_per_week?: number;
  start_date: string;
  end_date?: string | null;
  probation_end_date?: string | null;
  termination_date?: string | null;
  termination_reason?: string | null;
  is_current?: boolean;
}

export interface ContractUpdate {
  contract_number?: string | null;
  contract_type?: ContractType | null;
  job_title?: string | null;
  wage_type?: WageType | null;
  base_wage?: number | null;
  hours_per_week?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  probation_end_date?: string | null;
  termination_date?: string | null;
  termination_reason?: string | null;
  is_current?: boolean | null;
}

export interface ContractRead {
  id: string;
  tenant_id: string;
  employee_id: string;
  contract_number: string;
  contract_type: ContractType;
  job_title: string;
  wage_type: WageType;
  base_wage: number;
  hours_per_week: number;
  start_date: string;
  end_date: string | null;
  probation_end_date: string | null;
  termination_date: string | null;
  termination_reason: string | null;
  is_current: boolean;
  created_at: string;
  updated_at: string;
}
