// mirrors the document rules the backend enforces so the form can warn as you type
export type DocumentType = 'dni' | 'nie' | 'passport'

export const DOCUMENT_TYPES: DocumentType[] = ['dni', 'nie', 'passport']

const LETTERS = 'TRWAGMYFPDXBNJZSQVHLCKE'
const DNI_RE = /^\d{8}[A-Z]$/
const NIE_RE = /^[XYZ]\d{7}[A-Z]$/
const PASSPORT_RE = /^[A-Z0-9]{6,12}$/
const NIE_PREFIX: Record<string, string> = { X: '0', Y: '1', Z: '2' }

// normalises a typed document the same way the backend does before checking it
export function normaliseDocument(value: string): string {
  return value.trim().toUpperCase().replace(/[\s-]/g, '')
}

// checks the control letter a spanish identity number ends with
function validControlLetter(digits: string, letter: string): boolean {
  return LETTERS[parseInt(digits, 10) % 23] === letter
}

// reports whether a document is valid for the type it claims to be
export function isValidDocument(value: string, type: DocumentType): boolean {
  const v = normaliseDocument(value)
  if (type === 'dni') return DNI_RE.test(v) && validControlLetter(v.slice(0, 8), v[8]!)
  if (type === 'nie') {
    if (!NIE_RE.test(v)) return false
    return validControlLetter(NIE_PREFIX[v[0]!]! + v.slice(1, 8), v[8]!)
  }
  return PASSPORT_RE.test(v)
}
