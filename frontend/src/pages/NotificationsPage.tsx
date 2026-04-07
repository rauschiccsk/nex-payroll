import { useCallback, useEffect, useState } from 'react'
import type {
  NotificationRead,
  NotificationCreate,
  NotificationUpdate,
  NotificationType,
  NotificationSeverity,
} from '@/types/notification'
import {
  listNotifications,
  createNotification,
  updateNotification,
  deleteNotification,
} from '@/services/notification.service'
import { authStore } from '@/stores/auth.store'

// -- Constants ---------------------------------------------------------------
const PAGE_SIZE = 20

const TYPE_LABELS: Record<NotificationType, string> = {
  deadline: 'Termín',
  anomaly: 'Anomália',
  system: 'Systém',
  approval: 'Schválenie',
}

const TYPE_COLORS: Record<NotificationType, string> = {
  deadline: 'bg-orange-100 text-orange-800',
  anomaly: 'bg-red-100 text-red-800',
  system: 'bg-blue-100 text-blue-800',
  approval: 'bg-purple-100 text-purple-800',
}

const SEVERITY_LABELS: Record<NotificationSeverity, string> = {
  info: 'Info',
  warning: 'Varovanie',
  critical: 'Kritické',
}

const SEVERITY_COLORS: Record<NotificationSeverity, string> = {
  info: 'bg-blue-100 text-blue-800',
  warning: 'bg-yellow-100 text-yellow-800',
  critical: 'bg-red-100 text-red-800',
}

// -- Empty form state --------------------------------------------------------
interface FormState {
  tenant_id: string
  user_id: string
  type: NotificationType
  severity: NotificationSeverity
  title: string
  message: string
  related_entity: string
  related_entity_id: string
  is_read: boolean
}

const EMPTY_FORM: FormState = {
  tenant_id: '',
  user_id: '',
  type: 'system',
  severity: 'info',
  title: '',
  message: '',
  related_entity: '',
  related_entity_id: '',
  is_read: false,
}

// -- Helpers -----------------------------------------------------------------
function toCreatePayload(form: FormState): NotificationCreate {
  return {
    tenant_id: form.tenant_id,
    user_id: form.user_id,
    type: form.type,
    severity: form.severity,
    title: form.title,
    message: form.message,
    related_entity: form.related_entity || null,
    related_entity_id: form.related_entity_id || null,
  }
}

function toUpdatePayload(form: FormState): NotificationUpdate {
  return {
    type: form.type,
    severity: form.severity,
    title: form.title,
    message: form.message,
    related_entity: form.related_entity || null,
    related_entity_id: form.related_entity_id || null,
    is_read: form.is_read,
  }
}

function notificationToForm(n: NotificationRead): FormState {
  return {
    tenant_id: n.tenant_id,
    user_id: n.user_id,
    type: n.type,
    severity: n.severity,
    title: n.title,
    message: n.message,
    related_entity: n.related_entity ?? '',
    related_entity_id: n.related_entity_id ?? '',
    is_read: n.is_read,
  }
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('sk-SK')
}

// -- Component ---------------------------------------------------------------
function NotificationsPage() {
  // List state
  const [items, setItems] = useState<NotificationRead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail state
  const [detail, setDetail] = useState<NotificationRead | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<NotificationRead | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleting, setDeleting] = useState<NotificationRead | null>(null)

  // -- Fetch -----------------------------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listNotifications({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nepodarilo sa načítať dáta')
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
    const tenantId = authStore.getState().tenantId ?? ''
    setForm({ ...EMPTY_FORM, tenant_id: tenantId })
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(notification: NotificationRead) {
    setEditing(notification)
    setForm(notificationToForm(notification))
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
        await updateNotification(editing.id, toUpdatePayload(form))
      } else {
        await createNotification(toCreatePayload(form))
      }
      closeModal()
      await fetchData()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Chyba pri ukladaní')
    } finally {
      setSubmitting(false)
    }
  }

  // -- Delete handlers -------------------------------------------------------
  async function handleDelete() {
    if (!deleting) return
    try {
      await deleteNotification(deleting.id)
      setDeleting(null)
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri mazaní')
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
          <h1 className="text-2xl font-bold text-gray-900">Notifikácie</h1>
          <p className="mt-1 text-sm text-gray-600">
            Správa systémových notifikácií a upozornení
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          + Nová notifikácia
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
                Názov
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Typ
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Závažnosť
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Stav
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Vytvorené
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Akcie
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  Načítavam...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  Žiadne notifikácie
                </td>
              </tr>
            )}
            {!loading &&
              items.map((notif) => (
                <tr
                  key={notif.id}
                  className={`hover:bg-gray-50 ${!notif.is_read ? 'bg-blue-50/30' : ''}`}
                >
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {notif.title}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLORS[notif.type]}`}
                    >
                      {TYPE_LABELS[notif.type]}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_COLORS[notif.severity]}`}
                    >
                      {SEVERITY_LABELS[notif.severity]}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    {notif.is_read ? (
                      <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                        Prečítané
                      </span>
                    ) : (
                      <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                        Nové
                      </span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                    {formatDateTime(notif.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                    <button
                      onClick={() => setDetail(notif)}
                      className="mr-2 text-gray-600 hover:text-gray-800"
                    >
                      Detail
                    </button>
                    <button
                      onClick={() => openEdit(notif)}
                      className="mr-2 text-primary-600 hover:text-primary-800"
                    >
                      Upraviť
                    </button>
                    <button
                      onClick={() => setDeleting(notif)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Zmazať
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
              Zobrazených {page * PAGE_SIZE + 1}&ndash;
              {Math.min((page + 1) * PAGE_SIZE, total)} z {total}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Predchádzajúca
              </button>
              <span className="flex items-center px-2 text-sm text-gray-700">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Nasledujúca
              </button>
            </div>
          </div>
        )}
      </div>

      {/* -- Detail Modal ----------------------------------------------------- */}
      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                Notifikácia — {detail.title}
              </h2>
            </div>

            <div className="space-y-4">
              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Základné údaje</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Názov</dt>
                    <dd className="font-medium text-gray-900">{detail.title}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Typ</dt>
                    <dd>
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLORS[detail.type]}`}
                      >
                        {TYPE_LABELS[detail.type]}
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Závažnosť</dt>
                    <dd>
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_COLORS[detail.severity]}`}
                      >
                        {SEVERITY_LABELS[detail.severity]}
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Stav</dt>
                    <dd className="font-medium text-gray-900">
                      {detail.is_read ? 'Prečítané' : 'Nové'}
                    </dd>
                  </div>
                </dl>
              </fieldset>

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Správa</legend>
                <p className="text-sm text-gray-700">{detail.message}</p>
              </fieldset>

              {(detail.related_entity || detail.related_entity_id) && (
                <fieldset className="rounded-lg border border-gray-200 p-4">
                  <legend className="px-2 text-sm font-medium text-gray-500">
                    Súvisiaca entita
                  </legend>
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                    <div>
                      <dt className="text-gray-500">Entita</dt>
                      <dd className="font-medium text-gray-900">
                        {detail.related_entity ?? '—'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">ID entity</dt>
                      <dd className="font-medium text-gray-900">
                        {detail.related_entity_id ?? '—'}
                      </dd>
                    </div>
                  </dl>
                </fieldset>
              )}

              <fieldset className="rounded-lg border border-gray-200 p-4">
                <legend className="px-2 text-sm font-medium text-gray-500">Systém</legend>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <dt className="text-gray-500">Vytvorené</dt>
                    <dd className="font-medium text-gray-900">
                      {formatDateTime(detail.created_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Prečítané</dt>
                    <dd className="font-medium text-gray-900">
                      {formatDateTime(detail.read_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">User ID</dt>
                    <dd className="font-medium text-gray-900">
                      {detail.user_id.slice(0, 8)}...
                    </dd>
                  </div>
                </dl>
              </fieldset>
            </div>

            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => {
                  openEdit(detail)
                  setDetail(null)
                }}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                Upraviť
              </button>
              <button
                onClick={() => setDetail(null)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zavrieť
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
              {editing ? 'Upraviť notifikáciu' : 'Nová notifikácia'}
            </h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* User ID — only for create */}
              {!editing && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    User ID
                  </label>
                  <input
                    type="text"
                    required
                    value={form.user_id}
                    onChange={(e) => updateField('user_id', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="UUID používateľa"
                  />
                </div>
              )}

              {/* Title */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Názov</label>
                <input
                  type="text"
                  required
                  value={form.title}
                  onChange={(e) => updateField('title', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="Názov notifikácie"
                />
              </div>

              {/* Type + Severity */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Typ</label>
                  <select
                    required
                    value={form.type}
                    onChange={(e) => updateField('type', e.target.value as NotificationType)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    {(Object.keys(TYPE_LABELS) as NotificationType[]).map((type) => (
                      <option key={type} value={type}>
                        {TYPE_LABELS[type]}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Závažnosť
                  </label>
                  <select
                    required
                    value={form.severity}
                    onChange={(e) =>
                      updateField('severity', e.target.value as NotificationSeverity)
                    }
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  >
                    {(Object.keys(SEVERITY_LABELS) as NotificationSeverity[]).map((sev) => (
                      <option key={sev} value={sev}>
                        {SEVERITY_LABELS[sev]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Message */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Správa</label>
                <textarea
                  required
                  value={form.message}
                  onChange={(e) => updateField('message', e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="Text notifikácie..."
                />
              </div>

              {/* Related entity */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Súvisiaca entita
                  </label>
                  <input
                    type="text"
                    value={form.related_entity}
                    onChange={(e) => updateField('related_entity', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="napr. employee, payroll"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    ID entity
                  </label>
                  <input
                    type="text"
                    value={form.related_entity_id}
                    onChange={(e) => updateField('related_entity_id', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="UUID entity"
                  />
                </div>
              </div>

              {/* Is read — only for edit */}
              {editing && (
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_read"
                    checked={form.is_read}
                    onChange={(e) => updateField('is_read', e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="is_read" className="text-sm font-medium text-gray-700">
                    Označiť ako prečítané
                  </label>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Zrušiť
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {submitting ? 'Ukladám...' : editing ? 'Uložiť zmeny' : 'Vytvoriť'}
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
            <h2 className="mb-2 text-lg font-semibold text-gray-900">Potvrdiť zmazanie</h2>
            <p className="mb-4 text-sm text-gray-600">
              Naozaj chcete zmazať notifikáciu <strong>{deleting.title}</strong>?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleting(null)}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Zrušiť
              </button>
              <button
                onClick={handleDelete}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Zmazať
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default NotificationsPage
