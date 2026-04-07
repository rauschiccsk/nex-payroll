// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router'
import Sidebar from '@/components/layout/Sidebar'

function renderSidebar(initialRoute = '/') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Sidebar />
    </MemoryRouter>,
  )
}

describe('Sidebar', () => {
  it('renders brand name', () => {
    renderSidebar()
    expect(screen.getByText('NEX')).toBeInTheDocument()
    expect(screen.getByText('Payroll')).toBeInTheDocument()
  })

  it('renders main navigation links', () => {
    renderSidebar()
    const links = screen.getAllByRole('link')
    const hrefs = links.map((l) => l.getAttribute('href'))
    expect(hrefs).toContain('/')
    expect(hrefs).toContain('/employees')
    expect(hrefs).toContain('/payroll')
    expect(hrefs).toContain('/leaves')
    expect(hrefs).toContain('/reports')
    expect(hrefs).toContain('/notifications')
  })

  it('uses dynamic current year in annual route', () => {
    renderSidebar()
    const currentYear = new Date().getFullYear()
    const link = screen.getByText('Ročné zúčtovanie').closest('a')
    expect(link).toHaveAttribute('href', `/annual/${currentYear}`)
  })

  it('toggles settings section on click', async () => {
    const user = userEvent.setup()
    renderSidebar()

    // Settings items should not be visible initially (route is '/')
    expect(screen.queryByText('Používatelia')).not.toBeInTheDocument()

    // Click the settings button
    const settingsButton = screen.getByRole('button', { name: /nastavenia/i })
    await user.click(settingsButton)

    // Settings items should now be visible
    expect(screen.getByText('Používatelia')).toBeInTheDocument()
    expect(screen.getByText('Tenanty')).toBeInTheDocument()
    expect(screen.getByText('Audit log')).toBeInTheDocument()

    // Click again to collapse
    await user.click(settingsButton)
    expect(screen.queryByText('Používatelia')).not.toBeInTheDocument()
  })

  it('expands settings when navigated to /settings', () => {
    renderSidebar('/settings')
    // Settings should auto-expand when on settings route
    expect(screen.getByText('Používatelia')).toBeInTheDocument()
  })
})
