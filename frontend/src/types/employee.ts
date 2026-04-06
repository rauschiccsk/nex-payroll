// ---------------------------------------------------------------------------
// Employee types — matches backend app.schemas.employee
// ---------------------------------------------------------------------------

export type Gender = 'M' | 'F';
export type TaxDeclarationType = 'standard' | 'secondary' | 'none';
export type EmployeeStatus = 'active' | 'inactive' | 'terminated';

export interface EmployeeCreate {
  tenant_id: string;
  employee_number: string;
  first_name: string;
  last_name: string;
  title_before?: string | null;
  title_after?: string | null;
  birth_date: string;
  birth_number: string;
  gender: Gender;
  nationality?: string;
  address_street: string;
  address_city: string;
  address_zip: string;
  address_country?: string;
  bank_iban: string;
  bank_bic?: string | null;
  health_insurer_id: string;
  tax_declaration_type: TaxDeclarationType;
  nczd_applied?: boolean;
  pillar2_saver?: boolean;
  is_disabled?: boolean;
  status?: EmployeeStatus;
  hire_date: string;
  termination_date?: string | null;
}

export interface EmployeeUpdate {
  employee_number?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  title_before?: string | null;
  title_after?: string | null;
  birth_date?: string | null;
  birth_number?: string | null;
  gender?: Gender | null;
  nationality?: string | null;
  address_street?: string | null;
  address_city?: string | null;
  address_zip?: string | null;
  address_country?: string | null;
  bank_iban?: string | null;
  bank_bic?: string | null;
  health_insurer_id?: string | null;
  tax_declaration_type?: TaxDeclarationType | null;
  nczd_applied?: boolean | null;
  pillar2_saver?: boolean | null;
  is_disabled?: boolean | null;
  status?: EmployeeStatus | null;
  hire_date?: string | null;
  termination_date?: string | null;
}

export interface EmployeeRead {
  id: string;
  tenant_id: string;
  employee_number: string;
  first_name: string;
  last_name: string;
  title_before: string | null;
  title_after: string | null;
  birth_date: string;
  birth_number: string;
  gender: Gender;
  nationality: string;
  address_street: string;
  address_city: string;
  address_zip: string;
  address_country: string;
  bank_iban: string;
  bank_bic: string | null;
  health_insurer_id: string;
  tax_declaration_type: TaxDeclarationType;
  nczd_applied: boolean;
  pillar2_saver: boolean;
  is_disabled: boolean;
  status: EmployeeStatus;
  hire_date: string;
  termination_date: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}
