import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import type { Gender, TaxDeclarationType, EmployeeStatus } from '@/types/employee'
import type { HealthInsurerRead } from '@/types/health-insurer'
import { createEmployee } from '@/services/employee.service'
import { listHealthInsurers } from '@/services/health-insurer.service'
import { authStore } from '@/stores/auth.store'
import {
  GENDER_LABELS,
  TAX_LABELS,
  STATUS_LABELS,
  EMPTY_FORM,
  toCreatePayload,
  inputCls,
  labelCls,
} from '@/utils/employee-helpers'
import type { FormState } from '@/utils/employee-helpers'

// -- Steps -------------------------------------------------------------------
const STEPS = [
  { key: 'personal', label: 'Osobné údaje' },
  { key: 'address', label: 'Adresa' },
  { key: 'bank', label: 'Bankové údaje' },
  { key: 'employment', label: 'Pracovné údaje' },
] as const

type StepKey = (typeof STEPS)[number]['key']

// -- Component ---------------------------------------------------------------
function EmployeeFormPage() {
  const navigate = useNavigate()

  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [step, setStep] = useState<StepKey>('personal')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Health insurers lookup
  const [insurers, setInsurers] = useState<HealthInsurerRead[]>([])

  const fetchInsurers = useCallback(async () => {
    try {
      const res = await listHealthInsurers({ skip: 0, limit: 100 })
      setInsurers(res.items)
    } catch {
      // silently fail
    }
  }, [])

  useEffect(() => {
    fetchInsurers()
  }, [fetchInsurers])

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const stepIndex = STEPS.findIndex((s) => s.key === step)

  function goNext() {
    const next = STEPS[stepIndex + 1]
    if (stepIndex < STEPS.length - 1 && next) {
      setStep(next.key)
    }
  }

  function goPrev() {
    const prev = STEPS[stepIndex - 1]
    if (stepIndex > 0 && prev) {
      setStep(prev.key)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const tenantId = authStore.getState().tenantId ?? ''
      const created = await createEmployee(toCreatePayload(form, tenantId))
      navigate(`/employees/${created.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba pri vytváraní zamestnanca')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/employees')}
          className="mb-2 text-sm text-primary-600 hover:text-primary-800"
        >
          &larr; Späť na zoznam
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Nový zamestnanec</h1>
        <p className="mt-1 text-sm text-gray-600">Vytvorenie nového zamestnanca</p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s.key} className="flex items-center">
            {i > 0 && <div className="mx-2 h-px w-8 bg-gray-300" />}
            <button
              type="button"
              onClick={() => setStep(s.key)}
              className={`flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${
                s.key === step
                  ? 'bg-primary-600 text-white'
                  : i < stepIndex
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-500'
              }`}
            >
              <span>{i + 1}</span>
              <span className="hidden sm:inline">{s.label}</span>
            </button>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Form */}
      <form
        onSubmit={handleSubmit}
        className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
      >
        {/* Step 1: Personal */}
        {step === 'personal' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Osobné údaje</h2>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className={labelCls}>Číslo zamestnanca</label>
                <input
                  type="text"
                  required
                  value={form.employee_number}
                  onChange={(e) => updateField('employee_number', e.target.value)}
                  className={`${inputCls} font-mono`}
                  placeholder="napr. EMP001"
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
                  placeholder="napr. Ján"
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
                  placeholder="napr. Novák"
                />
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4">
              <div>
                <label className={labelCls}>
                  Titul pred <span className="text-gray-400">(vol.)</span>
                </label>
                <input
                  type="text"
                  value={form.title_before}
                  onChange={(e) => updateField('title_before', e.target.value)}
                  className={inputCls}
                  placeholder="napr. Ing."
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
                  placeholder="napr. PhD."
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
                <input
                  type="text"
                  value={form.nationality}
                  onChange={(e) => updateField('nationality', e.target.value)}
                  className={inputCls}
                  placeholder="SK"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
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
                  placeholder="napr. 900101/1234"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Address */}
        {step === 'address' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Adresa</h2>
            <div>
              <label className={labelCls}>Ulica</label>
              <input
                type="text"
                required
                value={form.address_street}
                onChange={(e) => updateField('address_street', e.target.value)}
                className={inputCls}
                placeholder="napr. Hlavná 1"
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className={labelCls}>Mesto</label>
                <input
                  type="text"
                  required
                  value={form.address_city}
                  onChange={(e) => updateField('address_city', e.target.value)}
                  className={inputCls}
                  placeholder="napr. Bratislava"
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
                  placeholder="napr. 81101"
                />
              </div>
              <div>
                <label className={labelCls}>Krajina</label>
                <input
                  type="text"
                  value={form.address_country}
                  onChange={(e) => updateField('address_country', e.target.value)}
                  className={inputCls}
                  placeholder="SK"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Bank */}
        {step === 'bank' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Bankové údaje</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelCls}>IBAN</label>
                <input
                  type="text"
                  required
                  value={form.bank_iban}
                  onChange={(e) => updateField('bank_iban', e.target.value)}
                  className={`${inputCls} font-mono`}
                  placeholder="SK..."
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
                  placeholder="napr. SUBASKBX"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Employment */}
        {step === 'employment' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Pracovné údaje</h2>
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
            <div className="grid grid-cols-3 gap-4">
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

            {/* Flags */}
            <div className="mt-4">
              <h3 className="mb-2 text-sm font-semibold uppercase text-gray-500">Príznaky</h3>
              <div className="flex flex-wrap gap-6">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="create_nczd"
                    checked={form.nczd_applied}
                    onChange={(e) => updateField('nczd_applied', e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="create_nczd" className="text-sm font-medium text-gray-700">
                    NCZD (nezdaniteľná časť)
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="create_pillar2"
                    checked={form.pillar2_saver}
                    onChange={(e) => updateField('pillar2_saver', e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="create_pillar2" className="text-sm font-medium text-gray-700">
                    Sporiteľ II. piliera
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="create_disabled"
                    checked={form.is_disabled}
                    onChange={(e) => updateField('is_disabled', e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="create_disabled" className="text-sm font-medium text-gray-700">
                    ZŤP (zdravotné postihnutie)
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="mt-6 flex justify-between border-t border-gray-200 pt-4">
          <div>
            {stepIndex > 0 && (
              <button
                type="button"
                onClick={goPrev}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Späť
              </button>
            )}
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => navigate('/employees')}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Zrušiť
            </button>
            {stepIndex < STEPS.length - 1 ? (
              <button
                type="button"
                onClick={goNext}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                Ďalej
              </button>
            ) : (
              <button
                type="submit"
                disabled={submitting}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {submitting ? 'Vytváram...' : 'Vytvoriť zamestnanca'}
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  )
}

export default EmployeeFormPage
