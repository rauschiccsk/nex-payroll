import { useParams } from 'react-router'

function MonthlyPaymentsPage() {
  const { year, month } = useParams<{ year: string; month: string }>()

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Mesačné platby</h1>
      <p className="mt-2 text-gray-600">
        Platobné príkazy a SEPA — {month}/{year}
      </p>
    </div>
  )
}

export default MonthlyPaymentsPage
