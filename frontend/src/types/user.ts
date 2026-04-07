// ---------------------------------------------------------------------------
// User types — matches backend app.schemas.user
// ---------------------------------------------------------------------------

export type UserRole = 'director' | 'accountant' | 'employee';

export interface UserCreate {
  tenant_id: string;
  employee_id?: string | null;
  username: string;
  email: string;
  password: string;
  role: UserRole;
  is_active?: boolean;
}

export interface UserUpdate {
  employee_id?: string | null;
  username?: string | null;
  email?: string | null;
  password?: string | null;
  role?: UserRole | null;
  is_active?: boolean | null;
}

export interface UserRead {
  id: string;
  tenant_id: string;
  employee_id: string | null;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  password_changed_at: string | null;
  created_at: string;
  updated_at: string;
}
