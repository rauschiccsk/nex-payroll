// ---------------------------------------------------------------------------
// Tenant types — matches backend app.schemas.tenant
// ---------------------------------------------------------------------------

export interface TenantCreate {
  name: string;
  ico: string;
  dic?: string | null;
  ic_dph?: string | null;
  address_street: string;
  address_city: string;
  address_zip: string;
  address_country?: string;
  bank_iban: string;
  bank_bic?: string | null;
  default_role?: string;
  is_active?: boolean;
}

export interface TenantUpdate {
  name?: string | null;
  ico?: string | null;
  dic?: string | null;
  ic_dph?: string | null;
  address_street?: string | null;
  address_city?: string | null;
  address_zip?: string | null;
  address_country?: string | null;
  bank_iban?: string | null;
  bank_bic?: string | null;
  default_role?: string | null;
  is_active?: boolean | null;
}

export interface TenantRead {
  id: string;
  name: string;
  ico: string;
  dic: string | null;
  ic_dph: string | null;
  address_street: string;
  address_city: string;
  address_zip: string;
  address_country: string;
  bank_iban: string;
  bank_bic: string | null;
  schema_name: string;
  default_role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
