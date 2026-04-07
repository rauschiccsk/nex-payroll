import { useCallback, useEffect, useState } from 'react'
import type { UserCreate, UserRead, UserRole, UserUpdate } from '@/types/user'
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
} from '@/services/user.service'
import { authStore } from '@/stores/auth.store'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

// -- Form state --------------------------------------------------------------
interface FormState {
  employee_id: string
  username: string
  email: string
  password: string
  role: UserRole
  is_active: boolean
}

const EMPTY_FORM: FormState = {
  employee_id: '',
  username: '',
  email: '',
  password: '',
  role: 'employee',
  is_active: true,
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState, tenantId: string): UserCreate {
  return {
    tenant_id: tenantId,
    employee_id: form.employee_id || null,
    username: form.username,
    email: form.email,
    password: form.password,
    role: form.role,
    is_active: form.is_active,
  }
}

function toUpdatePayload(form: FormState, original: UserRead): UserUpdate {
  const payload: UserUpdate = {}
  if (form.employee_id !== (original.employee_id ?? '')) {
    payload.employee_id = form.employee_id || null
  }
  if (form.username !== original.username) payload.username = form.username
  if (form.email !== original.email) payload.email = form.email
  if (form.password) payload.password = form.password
  if (form.role !== original.role) payload.role = form.role
  if (form.is_active !== original.is_active) payload.is_active = form.is_active
  return payload
}

function userToForm(user: UserRead): FormState {
  return {
    employee_id: user.employee_id ?? '',
    username: user.username,
    email: user.email,
    password: '',
    role: user.role,
    is_active: user.is_active,
  }
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '\u2014'
  return new Date(iso).toLocaleString('sk-SK')
}

const ROLE_LABELS: Record<UserRole, string> = {
  director: 'Riaditel',
  accountant: 'Uctovnik',
  employee: 'Zamestnanec',
}

const ROLE_COLORS: Record<UserRole, string> = {
  director: 'bg-purple-100 text-purple-800',
  accountant: 'bg-blue-100 text-blue-800',
  employee: 'bg-gray-100 text-gray-600',
}

// -- Component ---------------------------------------------------------------
function UserManagementPage() {
  const tenantId = authStore.getState().tenantId ?? ''

  // List state
  const [items, setItems] = useState<UserRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<UserRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Detail modal
  const [detail, setDetail] = useState<UserRead | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<UserRead | null>(null)

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listUsers({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
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

  function openEdit(user: UserRead) {
    setEditing(user)
    setForm(userToForm(user))
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
        await updateUser(editing.id, toUpdatePayload(form, editing))
      } else {
        await createUser(toCreatePayload(form, tenantId ?? ''))
      }
      closeModal()
      await fetchData()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Chyba pri ukladani')
    } finally {
      setSubmitting(false)
    }
  }

  // -- Delete handlers -------------------------------------------------------
  async function handleDelete() {
    if (!deleting) return
    try {
      await deleteUser(deleting.id)
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
          <h1 className="text-2xl font-bold text-gray-900">Sprava pouzivatelov</h1>
          <p className="mt-1 text-sm text-gray-600">
            Pouzivatelia, roly a pristupove opravnenia
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Novy pouzivatel
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
                Pouzivatel
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Email
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Rola
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Stav
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Posledne prihlasenie
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
                  Ziadni pouzivatelia
                </td>
              </tr>
            )}
            {!loading &&
              items.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    <button
                      onClick={() => setDetail(user)}
                      className="text-primary-600 hover:text-primary-800 hover:underline"
                    >
                      {user.username}
                    </button>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {user.email}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-center text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_COLORS[user.role]}`}
                    >
                      {ROLE_LABELS[user.role]}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-center text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        user.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {user.is_active ? 'Aktivny' : 'Neaktivny'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDateTime(user.last_login_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDateTime(user.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(user)}
                      className="mr-2 text-gray-600 hover:text-gray-800"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(user)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upravit
                    </button>
                    <button
                      onClick={() => setDeleting(user)}
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

      {/* -- Detail Modal ----------------------------------------------------- */}
      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Detail pouzivatela</h2>
              <button
                onClick={() => setDetail(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                &times;
              </button>
            </div>

            <dl className="space-y-3">
              <div className="grid grid-cols-3 gap-2">
                <dt className="text-sm font-medium text-gray-500">Username</dt>
                <dd className="col-span-2 text-sm text-gray-900">{detail.username}</dd>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <dt className="text-sm font-medium text-gray-500">Email</dt>
                <dd className="col-span-2 text-sm text-gray-900">{detail.email}</dd>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <dt className="text-sm font-medium text-gray-500">Rola</dt>
                <dd className="col-span-2">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_COLORS[detail.role]}`}
                  >
                    {ROLE_LABELS[detail.role]}
                  </span>
                </dd>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <dt className="text-sm font-medium text-gray-500">Stav</dt>
                <dd className="col-span-2">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      detail.is_active
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {detail.is_active ? 'Aktivny' : 'Neaktivny'}
                  </span>
                </dd>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <dt className="text-sm font-medium text-gray-500">Tenant ID</dt>
                <dd className="col-span-2 text-sm font-mono text-gray-900">
                  {detail.tenant_id}
                </dd>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <dt className="text-sm font-medium text-gray-500">Employee ID</dt>
                <dd className="col-span-2 text-sm font-mono text-gray-900">
                  {detail.employee_id ?? '\u2014'}
                </dd>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <dt className="text-sm font-medium text-gray-500">Posledne prihlasenie</dt>
                <dd className="col-span-2 text-sm text-gray-900">
                  {formatDateTime(detail.last_login_at)}
                </dd>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <dt className="text-sm font-medium text-gray-500">Heslo zmenene</dt>
                <dd className="col-span-2 text-sm text-gray-900">
                  {formatDateTime(detail.password_changed_at)}
                </dd>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <dt className="text-sm font-medium text-gray-500">Vytvorene</dt>
                <dd className="col-span-2 text-sm text-gray-900">
                  {formatDateTime(detail.created_at)}
                </dd>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <dt className="text-sm font-medium text-gray-500">Aktualizovane</dt>
                <dd className="col-span-2 text-sm text-gray-900">
                  {formatDateTime(detail.updated_at)}
                </dd>
              </div>
            </dl>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  setDetail(null)
                  openEdit(detail)
                }}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                Upravit
              </button>
              <button
                onClick={() => setDetail(null)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zavriet
              </button>
            </div>
          </div>
        </div>
      )}

      {/* -- Create/Edit Modal ------------------------------------------------ */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              {editing ? 'Upravit pouzivatela' : 'Novy pouzivatel'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Username + Email */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Pouzivatelske meno
                  </label>
                  <input
                    type="text"
                    required
                    value={form.username}
                    onChange={(e) => updateField('username', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. jan.novak"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
                  <input
                    type="email"
                    required
                    value={form.email}
                    onChange={(e) => updateField('email', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. jan.novak@firma.sk"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Heslo{' '}
                  {editing && (
                    <span className="text-gray-400">(ponechajte prazdne ak nechcete menit)</span>
                  )}
                </label>
                <input
                  type="password"
                  required={!editing}
                  value={form.password}
                  onChange={(e) => updateField('password', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder={editing ? '(bez zmeny)' : 'Zadajte heslo'}
                />
              </div>

              {/* Role */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Rola</label>
                <select
                  value={form.role}
                  onChange={(e) => updateField('role', e.target.value as UserRole)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  <option value="director">{ROLE_LABELS['director']}</option>
                  <option value="accountant">{ROLE_LABELS['accountant']}</option>
                  <option value="employee">{ROLE_LABELS['employee']}</option>
                </select>
              </div>

              {/* Employee ID */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Employee ID <span className="text-gray-400">(volitelne)</span>
                </label>
                <input
                  type="text"
                  value={form.employee_id}
                  onChange={(e) => updateField('employee_id', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="UUID zamestnanca"
                />
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
                  Aktivny
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
              Naozaj chcete zmazat pouzivatela <strong>{deleting.username}</strong> (
              {deleting.email})?
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

export default UserManagementPage
