import api from './api'
import { authStore } from '@/stores/auth.store'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface UserInfo {
  id: string
  email: string
  username: string
  role: string
  tenant_id: string
  is_active: boolean
}

const authService = {
  /** OAuth2 password flow login */
  login(data: LoginRequest): Promise<LoginResponse> {
    // FastAPI OAuth2 expects form-urlencoded
    const formData = new URLSearchParams()
    formData.append('username', data.username)
    formData.append('password', data.password)

    return api
      .post<LoginResponse>('/api/v1/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      .then((res) => {
        const { access_token } = res.data
        authStore.getState().setToken(access_token)
        return res.data
      })
  },

  /** Logout — discard in-memory token */
  logout(): Promise<void> {
    return api.post('/api/v1/auth/logout').then(() => {
      authStore.getState().clear()
    })
  },

  /** Get current user info */
  me(): Promise<UserInfo> {
    return api.get<UserInfo>('/api/v1/auth/me').then((res) => {
      // Store tenant_id for X-Tenant header
      authStore.getState().setTenantId(res.data.tenant_id)
      return res.data
    })
  },

  /** Change own password */
  changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return api
      .put('/api/v1/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      .then(() => undefined)
  },
}

export default authService
