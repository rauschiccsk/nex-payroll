import { useParams } from 'react-router'

function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Detail zamestnanca</h1>
      <p className="mt-2 text-gray-600">Zamestnanec ID: {id}</p>
    </div>
  )
}

export default EmployeeDetailPage
