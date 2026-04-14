import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import type { EmployeeRead } from '@/types/employee'
import type { HealthInsurerRead } from '@/types/health-insurer'
import { getEmployee, updateEmployee, deleteEmployee } from '@/services/employee.service'
import { listHealthInsurers } from '@/services/health-insurer.service'
import {
  GENDER_LABELS,
  TAX_LABELS,
  STATUS_LABELS,
  STATUS_COLORS,
  COUNTRY_OPTIONS,
  employeeToForm,
  toUpdatePayload,
  formatDate,
  fullName,
  inputCls,
  labelCls,
} from '@/utils/employee-helpers'
import type { FormState } from '@/utils/employee-helpers'
import type { Gender, TaxDeclarationType, EmployeeStatus } from '@/types/employee'

// -- Component ---------------------------------------------------------------
function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [employee, setEmployee] = useState<EmployeeRead | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Edit modal state
  const [editOpen, setEditOpen] = useState(false)
  const [form, setForm] = useState<FormState | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirm
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  // Health insurers lookup
  const [insurers, setInsurers] = useState<HealthInsurerRead[]>([])

  const fetchEmployee = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const emp = await getEmployee(id)
      setEmployee(emp)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nepodarilo sa načítať zamestnanca')
    } finally {
      setLoading(false)
    }
  }, [id])

  const fetchInsurers = useCallback(async () => {
    try {
      const res = await listHealthInsurers({ skip: 0, limit: 100 })
      setInsurers(res.items)
    } catch {
      // silently fail
    }
  }, [])

  useEffect(() => {
    fetchEmployee()
  }, [fetchEmployee])

  useEffect(() => {
    fetchInsurers()
  }, [fetchInsurers])

  function insurerName(insId: string): string {
    const ins = insurers.find((i) => i.id === insId)
    return ins ? `${ins.code} - ${ins.name}` : insId.slice(0, 8)
  }

  // -- Edit handlers ---------------------------------------------------------
  function openEdit() {
    if (!employee) return
    setForm(employeeToForm(employee))
    setFormError(null)
    setEditOpen(true)
  }

  function closeEdit() {
    setEditOpen(false)
    setForm(null)
    setFormError(null)
  }

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!employee || !form) return
    setSubmitting(true)
    setFormError(null)
    try {
      const updated = await updateEmployee(employee.id, toUpdatePayload(form))
      setEmployee(updated)
      closeEdit()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Chyba pri ukladaní')
    } finally {
      setSubmitting(false)
    }
  }

  // -- Delete handlers -------------------------------------------------------
  async function handleDelete() {
    if (!employee) return
    try {
      await deleteEmployee(employee.id)
      navigate('/employees')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri mazaní')
      setDeleteConfirm(false)
    }
  }

  // -- Render ----------------------------------------------------------------
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sm text-gray-500">Načítavam...</p>
      </div>
    )
  }

  if (error || !employee) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/employees')}
          className="text-sm text-primary-600 hover:text-primary-800"
        >
          &larr; Späť na zoznam
        </button>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error ?? 'Zamestnanec nebol nájdený'}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate('/employees')}
            className="mb-2 text-sm text-primary-600 hover:text-primary-800"
          >
            &larr; Späť na zoznam
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{fullName(employee)}</h1>
          <p className="mt-1 text-sm text-gray-600">
            Zamestnanec č. <span className="font-mono">{employee.employee_number}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${STATUS_COLORS[employee.status]}`}
          >
            {STATUS_LABELS[employee.status]}
          </span>
          <button
            onClick={openEdit}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Upraviť
          </button>
          <button
            onClick={() => setDeleteConfirm(true)}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            Zmazať
          </button>
        </div>
      </div>

      {/* Detail cards */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Personal */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">Osobné údaje</h3>
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div>
              <span className="text-gray-500">Meno:</span>{' '}
              <span className="font-medium">{employee.first_name}</span>
            </div>
            <div>
              <span className="text-gray-500">Priezvisko:</span>{' '}
              <span className="font-medium">{employee.last_name}</span>
            </div>
            <div>
              <span className="text-gray-500">Titul pred:</span>{' '}
              {employee.title_before ?? '\u2014'}
            </div>
            <div>
              <span className="text-gray-500">Titul za:</span>{' '}
              {employee.title_after ?? '\u2014'}
            </div>
            <div>
              <span className="text-gray-500">Pohlavie:</span>{' '}
              {GENDER_LABELS[employee.gender]}
            </div>
            <div>
              <span className="text-gray-500">Národnosť:</span> {employee.nationality}
            </div>
            <div>
              <span className="text-gray-500">Dátum narodenia:</span>{' '}
              {formatDate(employee.birth_date)}
            </div>
            <div>
              <span className="text-gray-500">Rodné číslo:</span>{' '}
              <span className="font-mono">{employee.birth_number}</span>
            </div>
          </div>
        </div>

        {/* Address */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">Adresa</h3>
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-gray-500">Ulica:</span> {employee.address_street}
            </div>
            <div>
              <span className="text-gray-500">Mesto:</span> {employee.address_city}
            </div>
            <div>
              <span className="text-gray-500">PSČ:</span> {employee.address_zip}
            </div>
            <div>
              <span className="text-gray-500">Krajina:</span> {employee.address_country}
            </div>
          </div>
        </div>

        {/* Bank */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">Bankové údaje</h3>
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-gray-500">IBAN:</span>{' '}
              <span className="font-mono">{employee.bank_iban}</span>
            </div>
            <div>
              <span className="text-gray-500">BIC:</span>{' '}
              <span className="font-mono">{employee.bank_bic ?? '\u2014'}</span>
            </div>
          </div>
        </div>

        {/* Employment */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">Pracovné údaje</h3>
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div>
              <span className="text-gray-500">Dátum nástupu:</span>{' '}
              {formatDate(employee.hire_date)}
            </div>
            <div>
              <span className="text-gray-500">Dátum ukončenia:</span>{' '}
              {formatDate(employee.termination_date)}
            </div>
            <div>
              <span className="text-gray-500">Poisťovňa:</span>{' '}
              {insurerName(employee.health_insurer_id)}
            </div>
            <div>
              <span className="text-gray-500">Daňové vyhlásenie:</span>{' '}
              {TAX_LABELS[employee.tax_declaration_type]}
            </div>
          </div>
        </div>

        {/* Flags */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm lg:col-span-2">
          <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">Príznaky</h3>
          <div className="flex flex-wrap gap-3">
            <span
              className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${employee.nczd_applied ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}
            >
              NCZD: {employee.nczd_applied ? 'Áno' : 'Nie'}
            </span>
            <span
              className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${employee.pillar2_saver ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'}`}
            >
              II. pilier: {employee.pillar2_saver ? 'Áno' : 'Nie'}
            </span>
            <span
              className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${employee.is_disabled ? 'bg-orange-100 text-orange-800' : 'bg-gray-100 text-gray-600'}`}
            >
              ZŤP: {employee.is_disabled ? 'Áno' : 'Nie'}
            </span>
          </div>
        </div>
      </div>

      {/* Timestamps */}
      <div className="text-xs text-gray-400">
        Vytvorené: {formatDate(employee.created_at)} | Aktualizované:{' '}
        {formatDate(employee.updated_at)}
        {employee.is_deleted && (
          <span className="ml-2 rounded bg-red-100 px-2 py-0.5 text-red-700">Zmazaný</span>
        )}
      </div>

      {/* -- Edit Modal ------------------------------------------------------- */}
      {editOpen && form && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Upraviť zamestnanca</h2>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Personal */}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold uppercase text-gray-500">
                  Osobné údaje
                </legend>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className={labelCls}>Číslo zamestnanca</label>
                    <input
                      type="text"
                      required
                      value={form.employee_number}
                      onChange={(e) => updateField('employee_number', e.target.value)}
                      className={`${inputCls} font-mono`}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Meno</label>
                    <input
                      type="text"
                      required
                      value={form.first_name}
                      onChange={(e) => updateField('first_name', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Priezvisko</label>
                    <input
                      type="text"
                      required
                      value={form.last_name}
                      onChange={(e) => updateField('last_name', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-4 gap-4">
                  <div>
                    <label className={labelCls}>
                      Titul pred <span className="text-gray-400">(vol.)</span>
                    </label>
                    <input
                      type="text"
                      value={form.title_before}
                      onChange={(e) => updateField('title_before', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>
                      Titul za <span className="text-gray-400">(vol.)</span>
                    </label>
                    <input
                      type="text"
                      value={form.title_after}
                      onChange={(e) => updateField('title_after', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Pohlavie</label>
                    <select
                      value={form.gender}
                      onChange={(e) => updateField('gender', e.target.value as Gender)}
                      className={inputCls}
                    >
                      <option value="M">{GENDER_LABELS['M']}</option>
                      <option value="F">{GENDER_LABELS['F']}</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Národnosť</label>
                    <select
                      value={form.nationality}
                      onChange={(e) => updateField('nationality', e.target.value)}
                      className={inputCls}
                    >
                      {COUNTRY_OPTIONS.map((c) => (
                        <option key={c.code} value={c.code}>
                          {c.code} - {c.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelCls}>Dátum narodenia</label>
                    <input
                      type="date"
                      required
                      value={form.birth_date}
                      onChange={(e) => updateField('birth_date', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Rodné číslo</label>
                    <input
                      type="text"
                      required
                      value={form.birth_number}
                      onChange={(e) => updateField('birth_number', e.target.value)}
                      className={`${inputCls} font-mono`}
                    />
                  </div>
                </div>
              </fieldset>

              {/* Address */}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold uppercase text-gray-500">
                  Adresa
                </legend>
                <div>
                  <label className={labelCls}>Ulica</label>
                  <input
                    type="text"
                    required
                    value={form.address_street}
                    onChange={(e) => updateField('address_street', e.target.value)}
                    className={inputCls}
                  />
                </div>
                <div className="mt-4 grid grid-cols-3 gap-4">
                  <div>
                    <label className={labelCls}>Mesto</label>
                    <input
                      type="text"
                      required
                      value={form.address_city}
                      onChange={(e) => updateField('address_city', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>PSČ</label>
                    <input
                      type="text"
                      required
                      value={form.address_zip}
                      onChange={(e) => updateField('address_zip', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Krajina</label>
                    <select
                      value={form.address_country}
                      onChange={(e) => updateField('address_country', e.target.value)}
                      className={inputCls}
                    >
                      {COUNTRY_OPTIONS.map((c) => (
                        <option key={c.code} value={c.code}>
                          {c.code} - {c.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </fieldset>

              {/* Bank */}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold uppercase text-gray-500">
                  Bankové údaje
                </legend>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelCls}>IBAN</label>
                    <input
                      type="text"
                      required
                      value={form.bank_iban}
                      onChange={(e) => updateField('bank_iban', e.target.value)}
                      className={`${inputCls} font-mono`}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>
                      BIC <span className="text-gray-400">(voliteľné)</span>
                    </label>
                    <input
                      type="text"
                      value={form.bank_bic}
                      onChange={(e) => updateField('bank_bic', e.target.value)}
                      className={`${inputCls} font-mono`}
                    />
                  </div>
                </div>
              </fieldset>

              {/* Employment */}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold uppercase text-gray-500">
                  Pracovné údaje
                </legend>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelCls}>Dátum nástupu</label>
                    <input
                      type="date"
                      required
                      value={form.hire_date}
                      onChange={(e) => updateField('hire_date', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>
                      Dátum ukončenia <span className="text-gray-400">(voliteľné)</span>
                    </label>
                    <input
                      type="date"
                      value={form.termination_date}
                      onChange={(e) => updateField('termination_date', e.target.value)}
                      className={inputCls}
                    />
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-3 gap-4">
                  <div>
                    <label className={labelCls}>Stav</label>
                    <select
                      value={form.status}
                      onChange={(e) => updateField('status', e.target.value as EmployeeStatus)}
                      className={inputCls}
                    >
                      <option value="active">{STATUS_LABELS['active']}</option>
                      <option value="inactive">{STATUS_LABELS['inactive']}</option>
                      <option value="terminated">{STATUS_LABELS['terminated']}</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Poisťovňa</label>
                    <select
                      required
                      value={form.health_insurer_id}
                      onChange={(e) => updateField('health_insurer_id', e.target.value)}
                      className={inputCls}
                    >
                      <option value="">-- Vyberte --</option>
                      {insurers.map((ins) => (
                        <option key={ins.id} value={ins.id}>
                          {ins.code} - {ins.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Daňové vyhlásenie</label>
                    <select
                      value={form.tax_declaration_type}
                      onChange={(e) =>
                        updateField('tax_declaration_type', e.target.value as TaxDeclarationType)
                      }
                      className={inputCls}
                    >
                      <option value="standard">{TAX_LABELS['standard']}</option>
                      <option value="secondary">{TAX_LABELS['secondary']}</option>
                      <option value="none">{TAX_LABELS['none']}</option>
                    </select>
                  </div>
                </div>
              </fieldset>

              {/* Flags */}
              <fieldset>
                <legend className="mb-2 text-sm font-semibold uppercase text-gray-500">
                  Príznaky
                </legend>
                <div className="flex flex-wrap gap-6">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="edit_nczd"
                      checked={form.nczd_applied}
                      onChange={(e) => updateField('nczd_applied', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <label htmlFor="edit_nczd" className="text-sm font-medium text-gray-700">
                      NCZD (nezdaniteľná časť)
                    </label>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="edit_pillar2"
                      checked={form.pillar2_saver}
                      onChange={(e) => updateField('pillar2_saver', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <label htmlFor="edit_pillar2" className="text-sm font-medium text-gray-700">
                      Sporiteľ II. piliera
                    </label>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="edit_disabled"
                      checked={form.is_disabled}
                      onChange={(e) => updateField('is_disabled', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <label htmlFor="edit_disabled" className="text-sm font-medium text-gray-700">
                      ZŤP (zdravotné postihnutie)
                    </label>
                  </div>
                </div>
              </fieldset>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeEdit}
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Zrušiť
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {submitting ? 'Ukladám...' : 'Uložiť zmeny'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* -- Delete Confirmation ---------------------------------------------- */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">Potvrdiť zmazanie</h2>
            <p className="mb-4 text-sm text-gray-600">
              Naozaj chcete zmazať zamestnanca{' '}
              <strong>
                {employee.first_name} {employee.last_name}
              </strong>{' '}
              ({employee.employee_number})?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(false)}
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

export default EmployeeDetailPage
