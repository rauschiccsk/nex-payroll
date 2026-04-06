import { useParams } from 'react-router'

function MonthlyReportsPage() {
  const { year, month } = useParams<{ year: string; month: string }>()

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Mesačné výkazy</h1>
      <p className="mt-2 text-gray-600">
        SP/ZP/DÚ výkazy — {month}/{year}
      </p>
    </div>
  )
}

export default MonthlyReportsPage
