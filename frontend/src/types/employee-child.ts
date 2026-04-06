// ---------------------------------------------------------------------------
// EmployeeChild types — matches backend app.schemas.employee_child
// ---------------------------------------------------------------------------

export interface EmployeeChildCreate {
  tenant_id: string;
  employee_id: string;
  first_name: string;
  last_name: string;
  birth_date: string;
  birth_number?: string | null;
  is_tax_bonus_eligible?: boolean;
  custody_from?: string | null;
  custody_to?: string | null;
}

export interface EmployeeChildUpdate {
  first_name?: string | null;
  last_name?: string | null;
  birth_date?: string | null;
  birth_number?: string | null;
  is_tax_bonus_eligible?: boolean | null;
  custody_from?: string | null;
  custody_to?: string | null;
}

export interface EmployeeChildRead {
  id: string;
  tenant_id: string;
  employee_id: string;
  first_name: string;
  last_name: string;
  birth_date: string;
  birth_number: string | null;
  is_tax_bonus_eligible: boolean;
  custody_from: string | null;
  custody_to: string | null;
  created_at: string;
  updated_at: string;
}
