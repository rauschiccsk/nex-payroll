// ---------------------------------------------------------------------------
// Shared employee helpers, labels, and form utilities
// ---------------------------------------------------------------------------

import type {
  EmployeeCreate,
  EmployeeRead,
  EmployeeUpdate,
  Gender,
  TaxDeclarationType,
  EmployeeStatus,
} from '@/types/employee'

// -- Labels ------------------------------------------------------------------
export const GENDER_LABELS: Record<Gender, string> = {
  M: 'Muž',
  F: 'Žena',
}

export const TAX_LABELS: Record<TaxDeclarationType, string> = {
  standard: 'Štandardné',
  secondary: 'Vedľajšie',
  none: 'Žiadne',
}

export const STATUS_LABELS: Record<EmployeeStatus, string> = {
  active: 'Aktívny',
  inactive: 'Neaktívny',
  terminated: 'Ukončený',
}

export const STATUS_COLORS: Record<EmployeeStatus, string> = {
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-yellow-100 text-yellow-800',
  terminated: 'bg-red-100 text-red-800',
}

// -- Form state --------------------------------------------------------------
export interface FormState {
  employee_number: string
  first_name: string
  last_name: string
  title_before: string
  title_after: string
  birth_date: string
  birth_number: string
  gender: Gender
  nationality: string
  address_street: string
  address_city: string
  address_zip: string
  address_country: string
  bank_iban: string
  bank_bic: string
  health_insurer_id: string
  tax_declaration_type: TaxDeclarationType
  nczd_applied: boolean
  pillar2_saver: boolean
  is_disabled: boolean
  status: EmployeeStatus
  hire_date: string
  termination_date: string
}

export const EMPTY_FORM: FormState = {
  employee_number: '',
  first_name: '',
  last_name: '',
  title_before: '',
  title_after: '',
  birth_date: '',
  birth_number: '',
  gender: 'M',
  nationality: 'SK',
  address_street: '',
  address_city: '',
  address_zip: '',
  address_country: 'SK',
  bank_iban: '',
  bank_bic: '',
  health_insurer_id: '',
  tax_declaration_type: 'standard',
  nczd_applied: true,
  pillar2_saver: false,
  is_disabled: false,
  status: 'active',
  hire_date: '',
  termination_date: '',
}

// -- Converters --------------------------------------------------------------
export function toCreatePayload(form: FormState, tenantId: string): EmployeeCreate {
  return {
    tenant_id: tenantId,
    employee_number: form.employee_number,
    first_name: form.first_name,
    last_name: form.last_name,
    title_before: form.title_before || null,
    title_after: form.title_after || null,
    birth_date: form.birth_date,
    birth_number: form.birth_number,
    gender: form.gender,
    nationality: form.nationality || 'SK',
    address_street: form.address_street,
    address_city: form.address_city,
    address_zip: form.address_zip,
    address_country: form.address_country || 'SK',
    bank_iban: form.bank_iban,
    bank_bic: form.bank_bic || null,
    health_insurer_id: form.health_insurer_id,
    tax_declaration_type: form.tax_declaration_type,
    nczd_applied: form.nczd_applied,
    pillar2_saver: form.pillar2_saver,
    is_disabled: form.is_disabled,
    status: form.status,
    hire_date: form.hire_date,
    termination_date: form.termination_date || null,
  }
}

export function toUpdatePayload(form: FormState): EmployeeUpdate {
  return {
    employee_number: form.employee_number,
    first_name: form.first_name,
    last_name: form.last_name,
    title_before: form.title_before || null,
    title_after: form.title_after || null,
    birth_date: form.birth_date,
    birth_number: form.birth_number,
    gender: form.gender,
    nationality: form.nationality || 'SK',
    address_street: form.address_street,
    address_city: form.address_city,
    address_zip: form.address_zip,
    address_country: form.address_country || 'SK',
    bank_iban: form.bank_iban,
    bank_bic: form.bank_bic || null,
    health_insurer_id: form.health_insurer_id,
    tax_declaration_type: form.tax_declaration_type,
    nczd_applied: form.nczd_applied,
    pillar2_saver: form.pillar2_saver,
    is_disabled: form.is_disabled,
    status: form.status,
    hire_date: form.hire_date,
    termination_date: form.termination_date || null,
  }
}

export function employeeToForm(emp: EmployeeRead): FormState {
  return {
    employee_number: emp.employee_number,
    first_name: emp.first_name,
    last_name: emp.last_name,
    title_before: emp.title_before ?? '',
    title_after: emp.title_after ?? '',
    birth_date: emp.birth_date,
    birth_number: emp.birth_number,
    gender: emp.gender,
    nationality: emp.nationality,
    address_street: emp.address_street,
    address_city: emp.address_city,
    address_zip: emp.address_zip,
    address_country: emp.address_country,
    bank_iban: emp.bank_iban,
    bank_bic: emp.bank_bic ?? '',
    health_insurer_id: emp.health_insurer_id,
    tax_declaration_type: emp.tax_declaration_type,
    nczd_applied: emp.nczd_applied,
    pillar2_saver: emp.pillar2_saver,
    is_disabled: emp.is_disabled,
    status: emp.status,
    hire_date: emp.hire_date,
    termination_date: emp.termination_date ?? '',
  }
}

// -- Helpers -----------------------------------------------------------------
export function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

export function fullName(emp: EmployeeRead): string {
  const parts: string[] = []
  if (emp.title_before) parts.push(emp.title_before)
  parts.push(emp.first_name, emp.last_name)
  if (emp.title_after) parts.push(emp.title_after)
  return parts.join(' ')
}

// -- CSS classes --------------------------------------------------------------
export const inputCls =
  'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500'
export const labelCls = 'mb-1 block text-sm font-medium text-gray-700'
