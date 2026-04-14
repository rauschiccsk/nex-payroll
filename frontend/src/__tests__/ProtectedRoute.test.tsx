import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, it, expect, beforeEach } from 'vitest'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { authStore } from '@/stores/auth.store'

function TestDashboard() {
  return <div>Dashboard Content</div>
}

function TestLogin() {
  return <div>Login Page</div>
}

function renderWithRouter(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<TestLogin />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <TestDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/employees"
          element={
            <ProtectedRoute>
              <div>Employees Page</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    authStore.getState().clear()
  })

  it('redirects to /login when no token is present', () => {
    renderWithRouter('/')
    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Dashboard Content')).not.toBeInTheDocument()
  })

  it('renders children when token is present', () => {
    authStore.getState().setToken('test-jwt-token')
    renderWithRouter('/')
    expect(screen.getByText('Dashboard Content')).toBeInTheDocument()
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
  })

  it('redirects from any protected route when not authenticated', () => {
    renderWithRouter('/employees')
    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Employees Page')).not.toBeInTheDocument()
  })

  it('allows access to any protected route when authenticated', () => {
    authStore.getState().setToken('test-jwt-token')
    renderWithRouter('/employees')
    expect(screen.getByText('Employees Page')).toBeInTheDocument()
  })
})
