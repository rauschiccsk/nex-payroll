import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock service modules before importing component
vi.mock('@/services/monthly-report.service', () => ({
  listMonthlyReports: vi.fn(),
  getMonthlyReport: vi.fn(),
  createMonthlyReport: vi.fn(),
  updateMonthlyReport: vi.fn(),
  deleteMonthlyReport: vi.fn(),
}))

vi.mock('@/stores/auth.store', () => ({
  authStore: {
    getState: () => ({ tenantId: 'tenant-aaa' }),
  },
}))

import MonthlyReportsPage from '@/pages/MonthlyReportsPage'
import {
  listMonthlyReports,
  createMonthlyReport,
  updateMonthlyReport,
  deleteMonthlyReport,
} from '@/services/monthly-report.service'
import type { MonthlyReportRead } from '@/types/monthly-report'

const MOCK_REPORT_1: MonthlyReportRead = {
  id: '11111111-1111-1111-1111-111111111111',
  tenant_id: 'tenant-aaa',
  period_year: 2026,
  period_month: 3,
  report_type: 'sp_monthly',
  file_path: '/reports/2026/03/sp_monthly.xml',
  file_format: 'xml',
  status: 'generated',
  deadline_date: '2026-04-20',
  institution: 'Sociálna poisťovňa',
  submitted_at: null,
  health_insurer_id: null,
  created_at: '2026-03-25T08:00:00Z',
  updated_at: '2026-03-25T08:00:00Z',
}

const MOCK_REPORT_2: MonthlyReportRead = {
  id: '22222222-2222-2222-2222-222222222222',
  tenant_id: 'tenant-aaa',
  period_year: 2026,
  period_month: 3,
  report_type: 'zp_vszp',
  file_path: '/reports/2026/03/zp_vszp.xml',
  file_format: 'xml',
  status: 'submitted',
  deadline_date: '2026-04-03',
  institution: 'Všeobecná zdravotná poisťovňa',
  submitted_at: '2026-04-01T10:30:00Z',
  health_insurer_id: 'hi-vszp',
  created_at: '2026-03-25T09:00:00Z',
  updated_at: '2026-04-01T10:30:00Z',
}

function mockListResponse(items: MonthlyReportRead[] = [MOCK_REPORT_1, MOCK_REPORT_2]) {
  vi.mocked(listMonthlyReports).mockResolvedValue({
    items,
    total: items.length,
    skip: 0,
    limit: 20,
  })
}

describe('MonthlyReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListResponse()
  })

  it('renders page heading and data table', async () => {
    render(<MonthlyReportsPage />)

    expect(screen.getByText('Mesačné výkazy')).toBeInTheDocument()
    expect(screen.getByText('+ Nový výkaz')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    expect(screen.getByText('ZP VšZP')).toBeInTheDocument()
    expect(screen.getByText('Sociálna poisťovňa')).toBeInTheDocument()
    expect(screen.getByText('Všeobecná zdravotná poisťovňa')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    vi.mocked(listMonthlyReports).mockReturnValue(new Promise(() => {}))
    render(<MonthlyReportsPage />)

    expect(screen.getByText('Načítavam...')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mockListResponse([])
    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('Žiadne záznamy')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    vi.mocked(listMonthlyReports).mockRejectedValue(new Error('Network error'))
    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('displays status badges with correct colors', async () => {
    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    // status 'generated' → blue badge
    const generatedBadge = screen.getByText('Vygenerovaný')
    expect(generatedBadge.className).toContain('bg-blue-100')

    // status 'submitted' → yellow badge
    const submittedBadge = screen.getByText('Odoslaný')
    expect(submittedBadge.className).toContain('bg-yellow-100')
  })

  it('displays period in MM/YYYY format', async () => {
    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    // period_month=3, period_year=2026 → "03/2026"
    const periodCells = screen.getAllByText('03/2026')
    expect(periodCells.length).toBeGreaterThanOrEqual(1)
  })

  it('opens create modal on button click', async () => {
    const user = userEvent.setup()
    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nový výkaz'))

    expect(screen.getByText('Nový mesačný výkaz')).toBeInTheDocument()
    expect(screen.getByText('Vytvoriť')).toBeInTheDocument()
    // Report type dropdown should be visible in create mode
    expect(screen.getByText('— Vyberte typ —')).toBeInTheDocument()
  })

  it('opens edit modal on Upraviť click', async () => {
    const user = userEvent.setup()
    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upraviť')
    await user.click(editButtons[0]!)

    expect(screen.getByText('Upraviť výkaz')).toBeInTheDocument()
    expect(screen.getByText('Uložiť zmeny')).toBeInTheDocument()
    // Check form is pre-filled with institution
    expect(screen.getByDisplayValue('Sociálna poisťovňa')).toBeInTheDocument()
  })

  it('submits create form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(createMonthlyReport).mockResolvedValue({
      ...MOCK_REPORT_1,
      id: '33333333-3333-3333-3333-333333333333',
    })

    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nový výkaz'))

    // Select report type
    const typeSelect = screen.getByDisplayValue('— Vyberte typ —')
    await user.selectOptions(typeSelect, 'sp_monthly')

    // Fill institution
    const institutionInput = screen.getByPlaceholderText('napr. Sociálna poisťovňa')
    await user.clear(institutionInput)
    await user.type(institutionInput, 'SP Bratislava')

    // Fill file path
    const filePathInput = screen.getByPlaceholderText('napr. /reports/2026/01/sp_monthly.xml')
    await user.type(filePathInput, '/reports/2026/03/sp.xml')

    // Fill deadline — find by input type=date in the form
    const dateInputs = document.querySelectorAll<HTMLInputElement>('input[type="date"]')
    const deadlineInput = dateInputs[0]!
    await user.type(deadlineInput, '2026-04-20')

    await user.click(screen.getByText('Vytvoriť'))

    await waitFor(() => {
      expect(createMonthlyReport).toHaveBeenCalledTimes(1)
    })

    // List refreshed
    expect(listMonthlyReports).toHaveBeenCalledTimes(2) // initial + after create
  })

  it('submits edit form and refreshes list', async () => {
    const user = userEvent.setup()
    vi.mocked(updateMonthlyReport).mockResolvedValue({
      ...MOCK_REPORT_1,
      status: 'submitted',
    })

    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Upraviť')
    await user.click(editButtons[0]!)

    // Change status
    const statusSelect = screen.getByDisplayValue('Vygenerovaný')
    await user.selectOptions(statusSelect, 'submitted')

    await user.click(screen.getByText('Uložiť zmeny'))

    await waitFor(() => {
      expect(updateMonthlyReport).toHaveBeenCalledWith(
        MOCK_REPORT_1.id,
        expect.objectContaining({
          status: 'submitted',
        }),
      )
    })
  })

  it('opens and confirms delete dialog', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteMonthlyReport).mockResolvedValue(undefined)

    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazať')
    await user.click(deleteButtons[0]!)

    // Confirm dialog
    expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()

    // Find the Zmazať button inside the confirmation dialog
    const confirmButton = screen.getAllByText('Zmazať').find(
      (btn) => btn.closest('.max-w-sm') !== null,
    )
    expect(confirmButton).toBeDefined()
    await user.click(confirmButton!)

    await waitFor(() => {
      expect(deleteMonthlyReport).toHaveBeenCalledWith(MOCK_REPORT_1.id)
    })
  })

  it('cancels delete dialog', async () => {
    const user = userEvent.setup()

    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazať')
    await user.click(deleteButtons[0]!)

    expect(screen.getByText('Potvrdiť zmazanie')).toBeInTheDocument()

    // Click Zrušiť
    const cancelButtons = screen.getAllByText('Zrušiť')
    await user.click(cancelButtons[cancelButtons.length - 1]!)

    expect(screen.queryByText('Potvrdiť zmazanie')).not.toBeInTheDocument()
    expect(deleteMonthlyReport).not.toHaveBeenCalled()
  })

  it('closes create modal on Zrušiť', async () => {
    const user = userEvent.setup()

    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nový výkaz'))
    expect(screen.getByText('Nový mesačný výkaz')).toBeInTheDocument()

    await user.click(screen.getByText('Zrušiť'))
    expect(screen.queryByText('Nový mesačný výkaz')).not.toBeInTheDocument()
  })

  it('shows form error on create failure', async () => {
    const user = userEvent.setup()
    vi.mocked(createMonthlyReport).mockRejectedValue(new Error('Duplicitný záznam'))

    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Nový výkaz'))

    // Select report type
    const typeSelect = screen.getByDisplayValue('— Vyberte typ —')
    await user.selectOptions(typeSelect, 'sp_monthly')

    // Fill required fields
    const institutionInput = screen.getByPlaceholderText('napr. Sociálna poisťovňa')
    await user.type(institutionInput, 'SP')

    const filePathInput = screen.getByPlaceholderText('napr. /reports/2026/01/sp_monthly.xml')
    await user.type(filePathInput, '/reports/test.xml')

    const dateInputs = document.querySelectorAll<HTMLInputElement>('input[type="date"]')
    const deadlineInput = dateInputs[0]!
    await user.type(deadlineInput, '2026-04-20')

    await user.click(screen.getByText('Vytvoriť'))

    await waitFor(() => {
      expect(screen.getByText('Duplicitný záznam')).toBeInTheDocument()
    })
  })

  it('opens detail modal on Detail click', async () => {
    const user = userEvent.setup()

    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    // Detail modal should show sections
    expect(screen.getByText('Obdobie a typ')).toBeInTheDocument()
    expect(screen.getByText('Súbor')).toBeInTheDocument()
    expect(screen.getByText('Termíny')).toBeInTheDocument()
    expect(screen.getByText('Systém')).toBeInTheDocument()
    expect(screen.getByText('Zavrieť')).toBeInTheDocument()
  })

  it('closes detail modal on Zavrieť click', async () => {
    const user = userEvent.setup()

    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    expect(screen.getByText('Obdobie a typ')).toBeInTheDocument()

    await user.click(screen.getByText('Zavrieť'))

    expect(screen.queryByText('Obdobie a typ')).not.toBeInTheDocument()
  })

  it('navigates from detail to edit', async () => {
    const user = userEvent.setup()

    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    const detailButtons = screen.getAllByText('Detail')
    await user.click(detailButtons[0]!)

    // Click Upraviť in detail modal
    const editInDetail = screen.getAllByText('Upraviť').find(
      (btn) => btn.closest('.max-w-2xl') !== null,
    )
    expect(editInDetail).toBeDefined()
    await user.click(editInDetail!)

    // Detail modal closed, edit modal open
    expect(screen.getByText('Upraviť výkaz')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Sociálna poisťovňa')).toBeInTheDocument()
  })

  it('shows delete error on failure', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteMonthlyReport).mockRejectedValue(new Error('Chyba servera'))

    render(<MonthlyReportsPage />)

    await waitFor(() => {
      expect(screen.getByText('SP mesačný výkaz')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByText('Zmazať')
    await user.click(deleteButtons[0]!)

    const confirmButton = screen.getAllByText('Zmazať').find(
      (btn) => btn.closest('.max-w-sm') !== null,
    )
    await user.click(confirmButton!)

    await waitFor(() => {
      expect(screen.getByText('Chyba servera')).toBeInTheDocument()
    })
  })
})
