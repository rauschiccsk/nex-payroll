// ---------------------------------------------------------------------------
// Notification types — matches backend app.schemas.notification
// ---------------------------------------------------------------------------

export type NotificationType = 'deadline' | 'anomaly' | 'system' | 'approval';
export type NotificationSeverity = 'info' | 'warning' | 'critical';

export interface NotificationCreate {
  tenant_id: string;
  user_id: string;
  type: NotificationType;
  severity?: NotificationSeverity;
  title: string;
  message: string;
  related_entity?: string | null;
  related_entity_id?: string | null;
}

export interface NotificationUpdate {
  type?: NotificationType | null;
  severity?: NotificationSeverity | null;
  title?: string | null;
  message?: string | null;
  related_entity?: string | null;
  related_entity_id?: string | null;
  is_read?: boolean | null;
  read_at?: string | null;
}

export interface NotificationRead {
  id: string;
  tenant_id: string;
  user_id: string;
  type: NotificationType;
  severity: NotificationSeverity;
  title: string;
  message: string;
  related_entity: string | null;
  related_entity_id: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}
