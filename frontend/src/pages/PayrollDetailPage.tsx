import { useParams } from 'react-router'

function PayrollDetailPage() {
  const { year, month, id } = useParams<{ year: string; month: string; id: string }>()

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Detail mzdy</h1>
      <p className="mt-2 text-gray-600">
        Obdobie: {month}/{year}, Zamestnanec ID: {id}
      </p>
    </div>
  )
}

export default PayrollDetailPage
