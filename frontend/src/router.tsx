import { createBrowserRouter } from 'react-router'
import { MainLayout } from './components/layout'
import ProtectedRoute from './components/auth/ProtectedRoute'
import {
  LoginPage,
  DashboardPage,
  EmployeesPage,
  EmployeeDetailPage,
  EmployeeFormPage,
  ContractsPage,
  PayrollPage,
  MonthlyPayrollPage,
  PayrollDetailPage,
  PaymentsPage,
  MonthlyPaymentsPage,
  ReportsPage,
  MonthlyReportsPage,
  LeavesPage,
  LeaveCalendarPage,
  AnnualPage,
  LedgerIntegrationPage,
  SettingsPage,
  UserManagementPage,
  ContributionRatesPage,
  HealthInsurersPage,
  StatutoryDeadlinesPage,
  TaxBracketsPage,
  TenantsPage,
  AuditLogsPage,
  EmployeeChildrenPage,
  LeaveEntitlementsPage,
  NotificationsPage,
  PaySlipsPage,
  NotFoundPage,
} from './pages'

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'employees', element: <EmployeesPage /> },
      { path: 'employees/new', element: <EmployeeFormPage /> },
      { path: 'employees/:id', element: <EmployeeDetailPage /> },
      { path: 'contracts', element: <ContractsPage /> },
      { path: 'payroll', element: <PayrollPage /> },
      { path: 'payroll/:year/:month', element: <MonthlyPayrollPage /> },
      { path: 'payroll/:year/:month/:id', element: <PayrollDetailPage /> },
      { path: 'payments', element: <PaymentsPage /> },
      { path: 'payments/:year/:month', element: <MonthlyPaymentsPage /> },
      { path: 'reports', element: <ReportsPage /> },
      { path: 'reports/:year/:month', element: <MonthlyReportsPage /> },
      { path: 'leaves', element: <LeavesPage /> },
      { path: 'leaves/calendar', element: <LeaveCalendarPage /> },
      { path: 'annual/:year', element: <AnnualPage /> },
      { path: 'integration/ledger', element: <LedgerIntegrationPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'settings/users', element: <UserManagementPage /> },
      { path: 'settings/contribution-rates', element: <ContributionRatesPage /> },
      { path: 'settings/health-insurers', element: <HealthInsurersPage /> },
      { path: 'settings/statutory-deadlines', element: <StatutoryDeadlinesPage /> },
      { path: 'settings/tax-brackets', element: <TaxBracketsPage /> },
      { path: 'settings/tenants', element: <TenantsPage /> },
      { path: 'settings/audit-logs', element: <AuditLogsPage /> },
      { path: 'employee-children', element: <EmployeeChildrenPage /> },
      { path: 'leave-entitlements', element: <LeaveEntitlementsPage /> },
      { path: 'notifications', element: <NotificationsPage /> },
      { path: 'payslips', element: <PaySlipsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export default router
