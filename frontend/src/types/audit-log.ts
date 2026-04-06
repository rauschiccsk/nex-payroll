// ---------------------------------------------------------------------------
// AuditLog types — matches backend app.schemas.audit_log
// ---------------------------------------------------------------------------

export type AuditAction = 'CREATE' | 'UPDATE' | 'DELETE';

export interface AuditLogCreate {
  tenant_id: string;
  user_id?: string | null;
  action: AuditAction;
  entity_type: string;
  entity_id: string;
  old_values?: Record<string, unknown> | null;
  new_values?: Record<string, unknown> | null;
  ip_address?: string | null;
}

export interface AuditLogRead {
  id: string;
  tenant_id: string;
  user_id: string | null;
  action: AuditAction;
  entity_type: string;
  entity_id: string;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}
