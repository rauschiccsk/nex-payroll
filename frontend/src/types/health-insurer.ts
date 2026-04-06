// ---------------------------------------------------------------------------
// HealthInsurer types — matches backend app.schemas.health_insurer
// ---------------------------------------------------------------------------

export interface HealthInsurerCreate {
  code: string;
  name: string;
  iban: string;
  bic?: string | null;
  is_active?: boolean;
}

export interface HealthInsurerUpdate {
  code?: string | null;
  name?: string | null;
  iban?: string | null;
  bic?: string | null;
  is_active?: boolean | null;
}

export interface HealthInsurerRead {
  id: string;
  code: string;
  name: string;
  iban: string;
  bic: string | null;
  is_active: boolean;
  created_at: string;
}
