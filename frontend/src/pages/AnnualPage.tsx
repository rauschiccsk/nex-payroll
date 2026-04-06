import { useParams } from 'react-router'

function AnnualPage() {
  const { year } = useParams<{ year: string }>()

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Ročné zúčtovanie</h1>
      <p className="mt-2 text-gray-600">Daňové vyrovnanie a potvrdenia — {year}</p>
    </div>
  )
}

export default AnnualPage
