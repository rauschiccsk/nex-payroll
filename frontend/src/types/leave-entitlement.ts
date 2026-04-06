// ---------------------------------------------------------------------------
// LeaveEntitlement types — matches backend app.schemas.leave_entitlement
// ---------------------------------------------------------------------------

export interface LeaveEntitlementCreate {
  tenant_id: string;
  employee_id: string;
  year: number;
  total_days: number;
  used_days?: number;
  remaining_days: number;
  carryover_days?: number;
}

export interface LeaveEntitlementUpdate {
  total_days?: number | null;
  used_days?: number | null;
  remaining_days?: number | null;
  carryover_days?: number | null;
}

export interface LeaveEntitlementRead {
  id: string;
  tenant_id: string;
  employee_id: string;
  year: number;
  total_days: number;
  used_days: number;
  remaining_days: number;
  carryover_days: number;
  created_at: string;
  updated_at: string;
}
