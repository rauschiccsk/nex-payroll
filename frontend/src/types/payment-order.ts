// ---------------------------------------------------------------------------
// PaymentOrder types — matches backend app.schemas.payment_order
// ---------------------------------------------------------------------------

export type PaymentType =
  | 'net_wage'
  | 'sp'
  | 'zp_vszp'
  | 'zp_dovera'
  | 'zp_union'
  | 'tax'
  | 'pillar2';

export type PaymentStatus = 'pending' | 'exported' | 'paid';

export interface PaymentOrderCreate {
  tenant_id: string;
  period_year: number;
  period_month: number;
  payment_type: PaymentType;
  recipient_name: string;
  recipient_iban: string;
  recipient_bic?: string | null;
  amount: number;
  variable_symbol?: string | null;
  specific_symbol?: string | null;
  constant_symbol?: string | null;
  reference?: string | null;
  status?: PaymentStatus;
  employee_id?: string | null;
  health_insurer_id?: string | null;
}

export interface PaymentOrderUpdate {
  recipient_name?: string | null;
  recipient_iban?: string | null;
  recipient_bic?: string | null;
  amount?: number | null;
  variable_symbol?: string | null;
  specific_symbol?: string | null;
  constant_symbol?: string | null;
  reference?: string | null;
  status?: PaymentStatus | null;
  employee_id?: string | null;
  health_insurer_id?: string | null;
}

export interface PaymentOrderRead {
  id: string;
  tenant_id: string;
  period_year: number;
  period_month: number;
  payment_type: PaymentType;
  recipient_name: string;
  recipient_iban: string;
  recipient_bic: string | null;
  amount: number;
  variable_symbol: string | null;
  specific_symbol: string | null;
  constant_symbol: string | null;
  reference: string | null;
  status: PaymentStatus;
  employee_id: string | null;
  health_insurer_id: string | null;
  created_at: string;
  updated_at: string;
}
