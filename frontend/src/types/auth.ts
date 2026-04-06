// ---------------------------------------------------------------------------
// Auth types — matches backend auth endpoints
// ---------------------------------------------------------------------------

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  id: string;
  email: string;
  username: string;
  role: string;
  tenant_id: string;
  is_active: boolean;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}
