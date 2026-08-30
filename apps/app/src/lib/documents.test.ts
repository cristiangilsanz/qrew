// tests the shared identity document rules
import { describe, expect, it } from 'vitest'

import { DOCUMENT_TYPES, isValidDocument, normaliseDocument } from './documents'

describe('normaliseDocument', () => {
  // verifies that spacing and separators never change the outcome
  it('strips spacing and separators and upper cases the value', () => {
    expect(normaliseDocument(' 00000001-r ')).toBe('00000001R')
  })
})

describe('isValidDocument', () => {
  // verifies that a dni is accepted only with its correct control letter
  it('accepts a dni whose control letter matches', () => {
    expect(isValidDocument('00000001R', 'dni')).toBe(true)
    expect(isValidDocument('00000001A', 'dni')).toBe(false)
  })

  // verifies that a nie is accepted only with its correct control letter
  it('accepts a nie whose control letter matches', () => {
    expect(isValidDocument('X1234567L', 'nie')).toBe(true)
    expect(isValidDocument('X1234567A', 'nie')).toBe(false)
  })

  // verifies that a foreign document is accepted on shape alone
  it('accepts any other document of a plausible length', () => {
    expect(isValidDocument('AB123456', 'other')).toBe(true)
    expect(isValidDocument('1234567890ABCDEFGHIJ', 'other')).toBe(true)
    expect(isValidDocument('AB12', 'other')).toBe(false)
    expect(isValidDocument('AB123456789012345678901', 'other')).toBe(false)
  })

  // verifies that a value valid for one type is not accepted for another
  it('rejects a document that does not match the declared type', () => {
    expect(isValidDocument('00000001R', 'nie')).toBe(false)
    expect(isValidDocument('X1234567L', 'dni')).toBe(false)
  })

  // verifies that every offered type is one the validator understands
  it('offers exactly the types the forms present', () => {
    expect(DOCUMENT_TYPES).toEqual(['dni', 'nie', 'other'])
  })
})
