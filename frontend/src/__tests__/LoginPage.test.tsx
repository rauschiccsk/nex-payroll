import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import LoginPage from '@/pages/LoginPage'
import { authStore } from '@/stores/auth.store'

// Mock auth service
vi.mock('@/services/auth.service', () => ({
  default: {
    login: vi.fn(),
    me: vi.fn(),
  },
}))

import authService from '@/services/auth.service'

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    authStore.getState().clear()
    vi.clearAllMocks()
  })

  it('renders the login form', () => {
    renderLoginPage()
    expect(screen.getByText('Prihlásenie')).toBeInTheDocument()
    expect(screen.getByLabelText('Používateľské meno')).toBeInTheDocument()
    expect(screen.getByLabelText('Heslo')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Prihlásiť sa' }),
    ).toBeInTheDocument()
  })

  it('shows error message on login failure', async () => {
    const user = userEvent.setup()
    vi.mocked(authService.login).mockRejectedValue(
      new Error('Invalid credentials'),
    )

    renderLoginPage()

    await user.type(screen.getByLabelText('Používateľské meno'), 'testuser')
    await user.type(screen.getByLabelText('Heslo'), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: 'Prihlásiť sa' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Invalid credentials',
    )
  })

  it('calls authService.login and authService.me on form submit', async () => {
    const user = userEvent.setup()
    vi.mocked(authService.login).mockResolvedValue({
      access_token: 'jwt-token',
      token_type: 'bearer',
    })
    vi.mocked(authService.me).mockResolvedValue({
      id: '1',
      email: 'test@example.com',
      username: 'testuser',
      role: 'director',
      tenant_id: 'tenant-1',
      is_active: true,
    })

    renderLoginPage()

    await user.type(screen.getByLabelText('Používateľské meno'), 'testuser')
    await user.type(screen.getByLabelText('Heslo'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Prihlásiť sa' }))

    expect(authService.login).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'password123',
    })
    expect(authService.me).toHaveBeenCalled()
  })

  it('disables inputs and button while loading', async () => {
    const user = userEvent.setup()
    // Make login hang to observe loading state
    vi.mocked(authService.login).mockImplementation(
      () => new Promise(() => {}), // never resolves
    )

    renderLoginPage()

    await user.type(screen.getByLabelText('Používateľské meno'), 'testuser')
    await user.type(screen.getByLabelText('Heslo'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Prihlásiť sa' }))

    expect(screen.getByLabelText('Používateľské meno')).toBeDisabled()
    expect(screen.getByLabelText('Heslo')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Prihlasujem...' })).toBeDisabled()
  })
})
