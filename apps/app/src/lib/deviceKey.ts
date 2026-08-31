// holds the signing key that identifies this device to the server
const DB_NAME = 'qrew-device'
const STORE = 'keys'
const KEY_ID = 'binding'

// opens the small store the key pair lives in
function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    // creates the store the first time the database is opened
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(new Error('Device store unavailable.'))
  })
}

// reads or writes the stored pair through one short transaction
function withStore<T>(
  mode: IDBTransactionMode,
  run: (store: IDBObjectStore) => IDBRequest,
): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const request = run(db.transaction(STORE, mode).objectStore(STORE))
        request.onsuccess = () => resolve(request.result as T)
        request.onerror = () => reject(new Error('Device store unavailable.'))
      }),
  )
}

// encodes bytes the way the server decodes them
function toBase64Url(bytes: ArrayBuffer): string {
  const binary = String.fromCharCode(...new Uint8Array(bytes))
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

// returns the pair this device signs with, generating it the first time it is asked
async function loadOrCreateKeyPair(): Promise<CryptoKeyPair> {
  const stored = await withStore<CryptoKeyPair | undefined>('readonly', (store) =>
    store.get(KEY_ID),
  )
  if (stored) return stored

  // the private half is not extractable, so it cannot leave the device even in script
  const pair = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, false, [
    'sign',
    'verify',
  ])
  await withStore('readwrite', (store) => store.put(pair, KEY_ID))
  return pair
}

// reports whether this browser can hold a device key at all
export function deviceKeysSupported(): boolean {
  return typeof indexedDB !== 'undefined' && typeof crypto?.subtle?.generateKey === 'function'
}

// hands over the public half in the format the server expects
export async function devicePublicKey(): Promise<string> {
  const pair = await loadOrCreateKeyPair()
  return toBase64Url(await crypto.subtle.exportKey('spki', pair.publicKey))
}

// signs the challenge the server issued for this binding
export async function signChallenge(challenge: string): Promise<string> {
  const pair = await loadOrCreateKeyPair()
  const signature = await crypto.subtle.sign(
    { name: 'ECDSA', hash: 'SHA-256' },
    pair.privateKey,
    new TextEncoder().encode(challenge),
  )
  return toBase64Url(signature)
}

// forgets the key, so a device that was revoked can be trusted again from scratch
export async function forgetDeviceKey(): Promise<void> {
  await withStore('readwrite', (store) => store.delete(KEY_ID))
}
