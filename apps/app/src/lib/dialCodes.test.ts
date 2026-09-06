// tests the dialling code helpers behind the phone field
import { describe, expect, it } from 'vitest'

import { DEFAULT_DIAL_ISO, DIAL_CODES, splitDialCode, toE164 } from './dialCodes'

describe('DIAL_CODES', () => {
  // verifies that the list is usable as a picker
  it('carries a flag and a plus prefixed code for every entry', () => {
    expect(DIAL_CODES.length).toBeGreaterThan(200)
    for (const code of DIAL_CODES.slice(0, 25)) {
      expect(code.dial.startsWith('+')).toBe(true)
      expect(code.iso).toHaveLength(2)
      expect(code.flag.length).toBeGreaterThan(0)
    }
  })

  // verifies that the default the form starts on exists in the list
  it('includes the default country', () => {
    expect(DIAL_CODES.some((c) => c.iso === DEFAULT_DIAL_ISO)).toBe(true)
  })
})

describe('toE164', () => {
  // verifies that the api receives a single joined number
  it('joins the code and the national part and drops formatting', () => {
    expect(toE164('ES', '612 345 678')).toBe('+34612345678')
  })

  // verifies that an unknown country cannot silently produce a bare number
  it('returns only the digits when the country is unknown', () => {
    expect(toE164('ZZ', '612345678')).toBe('612345678')
  })
})

describe('splitDialCode', () => {
  // verifies that a stored number can be shown back in the two fields
  it('splits a stored number into its code and national part', () => {
    expect(splitDialCode('+34612345678')).toEqual({ iso: 'ES', national: '612345678' })
  })

  // verifies that a number without a known prefix falls back to the default
  it('falls back to the default country when no code matches', () => {
    expect(splitDialCode('612345678')).toEqual({
      iso: DEFAULT_DIAL_ISO,
      national: '612345678',
    })
  })
})
