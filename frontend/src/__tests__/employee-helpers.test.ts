import { describe, it, expect } from 'vitest'
import {
  toCreatePayload,
  toUpdatePayload,
  EMPTY_FORM,
  COUNTRY_OPTIONS,
} from '@/utils/employee-helpers'
import type { FormState } from '@/utils/employee-helpers'

describe('employee-helpers', () => {
  describe('COUNTRY_OPTIONS', () => {
    it('contains only 2-letter ISO codes', () => {
      for (const opt of COUNTRY_OPTIONS) {
        expect(opt.code).toMatch(/^[A-Z]{2}$/)
        expect(opt.label.length).toBeGreaterThan(0)
      }
    })

    it('has SK as first option', () => {
      expect(COUNTRY_OPTIONS[0]?.code).toBe('SK')
    })
  })

  describe('toCreatePayload — BUG-005 regression', () => {
    const baseForm: FormState = {
      ...EMPTY_FORM,
      employee_number: 'E001',
      first_name: 'Ján',
      last_name: 'Novák',
      birth_date: '1990-01-15',
      birth_number: '900115/1234',
      address_street: 'Hlavná 1',
      address_city: 'Bratislava',
      address_zip: '81101',
      bank_iban: 'SK3112000000198742637541',
      health_insurer_id: 'hi-1',
      hire_date: '2020-01-01',
    }

    it('sends 2-char address_country when value is a valid ISO code', () => {
      const payload = toCreatePayload({ ...baseForm, address_country: 'CZ' }, 'tenant-1')
      expect(payload.address_country).toBe('CZ')
    })

    it('truncates address_country to 2 chars if longer string provided', () => {
      const payload = toCreatePayload(
        { ...baseForm, address_country: 'Slovensko' },
        'tenant-1',
      )
      expect(payload.address_country).toBe('SL')
      expect(payload.address_country!.length).toBeLessThanOrEqual(2)
    })

    it('uppercases address_country', () => {
      const payload = toCreatePayload({ ...baseForm, address_country: 'sk' }, 'tenant-1')
      expect(payload.address_country).toBe('SK')
    })

    it('defaults address_country to SK when empty', () => {
      const payload = toCreatePayload({ ...baseForm, address_country: '' }, 'tenant-1')
      expect(payload.address_country).toBe('SK')
    })

    it('sends 2-char nationality', () => {
      const payload = toCreatePayload({ ...baseForm, nationality: 'CZ' }, 'tenant-1')
      expect(payload.nationality).toBe('CZ')
    })

    it('truncates nationality to 2 chars if longer string provided', () => {
      const payload = toCreatePayload({ ...baseForm, nationality: 'Slovak' }, 'tenant-1')
      expect(payload.nationality!.length).toBeLessThanOrEqual(2)
    })

    it('defaults nationality to SK when empty', () => {
      const payload = toCreatePayload({ ...baseForm, nationality: '' }, 'tenant-1')
      expect(payload.nationality).toBe('SK')
    })
  })

  describe('toUpdatePayload — BUG-005 regression', () => {
    const baseForm: FormState = {
      ...EMPTY_FORM,
      employee_number: 'E001',
      first_name: 'Ján',
      last_name: 'Novák',
      birth_date: '1990-01-15',
      birth_number: '900115/1234',
      address_street: 'Hlavná 1',
      address_city: 'Bratislava',
      address_zip: '81101',
      bank_iban: 'SK3112000000198742637541',
      health_insurer_id: 'hi-1',
      hire_date: '2020-01-01',
    }

    it('truncates address_country to 2 chars', () => {
      const payload = toUpdatePayload({ ...baseForm, address_country: 'Slovensko' })
      expect(payload.address_country!.length).toBeLessThanOrEqual(2)
    })

    it('uppercases and truncates nationality', () => {
      const payload = toUpdatePayload({ ...baseForm, nationality: 'czech' })
      expect(payload.nationality).toBe('CZ')
    })

    it('defaults to SK when empty', () => {
      const payload = toUpdatePayload({ ...baseForm, address_country: '', nationality: '' })
      expect(payload.address_country).toBe('SK')
      expect(payload.nationality).toBe('SK')
    })
  })
})
