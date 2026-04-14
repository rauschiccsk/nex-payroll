import { useCallback, useEffect, useState } from 'react'
import type { TenantRead, TenantCreate, TenantUpdate } from '@/types/tenant'
import {
  listTenants,
  createTenant,
  updateTenant,
  deleteTenant,
} from '@/services/tenant.service'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

// -- Empty form state --------------------------------------------------------
interface FormState {
  name: string
  ico: string
  dic: string
  ic_dph: string
  address_street: string
  address_city: string
  address_zip: string
  address_country: string
  bank_iban: string
  bank_bic: string
  default_role: string
  is_active: boolean
}

const EMPTY_FORM: FormState = {
  name: '',
  ico: '',
  dic: '',
  ic_dph: '',
  address_street: '',
  address_city: '',
  address_zip: '',
  address_country: 'SK',
  bank_iban: '',
  bank_bic: '',
  default_role: 'accountant',
  is_active: true,
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): TenantCreate {
  return {
    name: form.name.trim(),
    ico: form.ico.trim(),
    dic: form.dic.trim() || null,
    ic_dph: form.ic_dph.trim() || null,
    address_street: form.address_street.trim(),
    address_city: form.address_city.trim(),
    address_zip: form.address_zip.trim(),
    address_country: form.address_country.trim() || 'SK',
    bank_iban: form.bank_iban.trim(),
    bank_bic: form.bank_bic.trim() || null,
    default_role: form.default_role,
    is_active: form.is_active,
  }
}

function toUpdatePayload(form: FormState): TenantUpdate {
  return {
    name: form.name.trim(),
    ico: form.ico.trim(),
    dic: form.dic.trim() || null,
    ic_dph: form.ic_dph.trim() || null,
    address_street: form.address_street.trim(),
    address_city: form.address_city.trim(),
    address_zip: form.address_zip.trim(),
    address_country: form.address_country.trim() || 'SK',
    bank_iban: form.bank_iban.trim(),
    bank_bic: form.bank_bic.trim() || null,
    default_role: form.default_role,
    is_active: form.is_active,
  }
}

function tenantToForm(tenant: TenantRead): FormState {
  return {
    name: tenant.name,
    ico: tenant.ico,
    dic: tenant.dic ?? '',
    ic_dph: tenant.ic_dph ?? '',
    address_street: tenant.address_street,
    address_city: tenant.address_city,
    address_zip: tenant.address_zip,
    address_country: tenant.address_country,
    bank_iban: tenant.bank_iban,
    bank_bic: tenant.bank_bic ?? '',
    default_role: tenant.default_role,
    is_active: tenant.is_active,
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleDateString('sk-SK')
}

const ROLE_LABELS: Record<string, string> = {
  director: 'Riaditel',
  accountant: 'Uctovnik',
  employee: 'Zamestnanec',
}

// -- Component ---------------------------------------------------------------
function TenantsPage() {
  // List state
  const [items, setItems] = useState<TenantRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<TenantRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<TenantRead | null>(null)

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listTenants({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nepodarilo sa nacitat data')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // -- Modal handlers --------------------------------------------------------
  function openCreate() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(tenant: TenantRead) {
    setEditing(tenant)
    setForm(tenantToForm(tenant))
    setFormError(null)
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setEditing(null)
    setFormError(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setFormError(null)
    try {
      if (editing) {
        await updateTenant(editing.id, toUpdatePayload(form))
      } else {
        await createTenant(toCreatePayload(form))
      }
      closeModal()
      await fetchData()
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message)
      } else {
        setFormError('Chyba pri ukladani')
      }
    } finally {
      setSubmitting(false)
    }
  }

  // -- Delete handlers -------------------------------------------------------
  async function handleDelete() {
    if (!deleting) return
    try {
      await deleteTenant(deleting.id)
      setDeleting(null)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri mazani')
      setDeleting(null)
    }
  }

  // -- Form field updater ----------------------------------------------------
  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // -- Render ----------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Organizacie</h1>
          <p className="mt-1 text-sm text-gray-600">
            Sprava organizacii (tenantov) a ich zakladnych udajov
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nova organizacia
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Nazov
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                ICO
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Mesto
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                IBAN
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Stav
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Vytvorene
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Akcie
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                  Nacitavam...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                  Ziadne organizacie
                </td>
              </tr>
            )}
            {!loading &&
              items.map((tenant) => (
                <tr key={tenant.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {tenant.name}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-mono text-gray-700">
                    {tenant.ico}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {tenant.address_city}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-mono text-gray-700">
                    {tenant.bank_iban}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-center text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        tenant.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {tenant.is_active ? 'Aktivna' : 'Neaktivna'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDate(tenant.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => openEdit(tenant)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upravit
                    </button>
                    <button
                      onClick={() => setDeleting(tenant)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Zmazat
                    </button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3">
            <p className="text-sm text-gray-700">
              Zobrazenych {page * PAGE_SIZE + 1}&ndash;{Math.min((page + 1) * PAGE_SIZE, total)} z{' '}
              {total}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Predchadzajuca
              </button>
              <span className="flex items-center px-2 text-sm text-gray-700">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Nasledujuca
              </button>
            </div>
          </div>
        )}
      </div>

      {/* -- Create/Edit Modal ------------------------------------------------ */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              {editing ? 'Upravit organizaciu' : 'Nova organizacia'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name + ICO */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Nazov</label>
                  <input
                    type="text"
                    required
                    value={form.name}
                    onChange={(e) => updateField('name', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. Firma s.r.o."
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">ICO</label>
                  <input
                    type="text"
                    required
                    value={form.ico}
                    onChange={(e) => updateField('ico', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 12345678"
                  />
                </div>
              </div>

              {/* DIC + IC DPH */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    DIC <span className="text-gray-400">(volitelne)</span>
                  </label>
                  <input
                    type="text"
                    value={form.dic}
                    onChange={(e) => updateField('dic', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 2012345678"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    IC DPH <span className="text-gray-400">(volitelne)</span>
                  </label>
                  <input
                    type="text"
                    value={form.ic_dph}
                    onChange={(e) => updateField('ic_dph', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. SK2012345678"
                  />
                </div>
              </div>

              {/* Address */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Ulica</label>
                <input
                  type="text"
                  required
                  value={form.address_street}
                  onChange={(e) => updateField('address_street', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="napr. Hlavna 1"
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Mesto</label>
                  <input
                    type="text"
                    required
                    value={form.address_city}
                    onChange={(e) => updateField('address_city', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. Bratislava"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">PSC</label>
                  <input
                    type="text"
                    required
                    value={form.address_zip}
                    onChange={(e) => updateField('address_zip', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. 81101"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Krajina</label>
                  <select
                    value={form.address_country}
                    onChange={(e) => updateField('address_country', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    <option value="SK">SK - Slovensko</option>
                    <option value="CZ">CZ - Cesko</option>
                    <option value="HU">HU - Madarsko</option>
                    <option value="PL">PL - Polsko</option>
                    <option value="AT">AT - Rakusko</option>
                    <option value="DE">DE - Nemecko</option>
                    <option value="UA">UA - Ukrajina</option>
                  </select>
                </div>
              </div>

              {/* Bank details */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">IBAN</label>
                  <input
                    type="text"
                    required
                    value={form.bank_iban}
                    onChange={(e) => updateField('bank_iban', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="SK..."
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    BIC <span className="text-gray-400">(volitelne)</span>
                  </label>
                  <input
                    type="text"
                    value={form.bank_bic}
                    onChange={(e) => updateField('bank_bic', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. SUBASKBX"
                  />
                </div>
              </div>

              {/* Default role */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Predvolena rola
                </label>
                <select
                  value={form.default_role}
                  onChange={(e) => updateField('default_role', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  <option value="director">{ROLE_LABELS['director']}</option>
                  <option value="accountant">{ROLE_LABELS['accountant']}</option>
                  <option value="employee">{ROLE_LABELS['employee']}</option>
                </select>
              </div>

              {/* Is Active */}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={form.is_active}
                  onChange={(e) => updateField('is_active', e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                  Aktivna
                </label>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Zrusit
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {submitting ? 'Ukladam...' : editing ? 'Ulozit zmeny' : 'Vytvorit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* -- Delete Confirmation ---------------------------------------------- */}
      {deleting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">Potvrdit zmazanie</h2>
            <p className="mb-4 text-sm text-gray-600">
              Naozaj chcete zmazat organizaciu <strong>{deleting.name}</strong> ({deleting.ico})?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleting(null)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zrusit
              </button>
              <button
                onClick={handleDelete}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Zmazat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TenantsPage
