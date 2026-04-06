import { describe, it, expect } from 'vitest'
import type { UserInfo } from '@/services/auth.service'

describe('UserInfo type', () => {
  it('id and tenant_id are strings (UUIDs), not numbers', () => {
    const user: UserInfo = {
      id: '550e8400-e29b-41d4-a716-446655440000',
      email: 'test@example.com',
      username: 'testuser',
      role: 'accountant',
      tenant_id: '660e8400-e29b-41d4-a716-446655440001',
      is_active: true,
    }

    expect(typeof user.id).toBe('string')
    expect(typeof user.tenant_id).toBe('string')
  })

  it('uses username field instead of full_name', () => {
    const user: UserInfo = {
      id: '550e8400-e29b-41d4-a716-446655440000',
      email: 'test@example.com',
      username: 'janko',
      role: 'director',
      tenant_id: '660e8400-e29b-41d4-a716-446655440001',
      is_active: true,
    }

    expect(user.username).toBe('janko')
    // Verify full_name is NOT a property
    expect('full_name' in user).toBe(false)
  })
})
