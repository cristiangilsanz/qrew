// tests the signing key that identifies this device to the server
import 'fake-indexeddb/auto'

import { beforeEach, describe, expect, it } from 'vitest'

import { deviceKeysSupported, devicePublicKey, forgetDeviceKey, signChallenge } from './deviceKey'

// decodes what the module encodes for the wire
function fromBase64Url(value: string): Uint8Array {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/')
  const binary = atob(padded.padEnd(Math.ceil(padded.length / 4) * 4, '='))
  return Uint8Array.from(binary, (c) => c.charCodeAt(0))
}

describe('device key', () => {
  beforeEach(async () => {
    await forgetDeviceKey()
  })

  it('reports whether this browser can hold one', () => {
    expect(deviceKeysSupported()).toBe(true)
  })

  it('hands over a public key the server can read', async () => {
    const exported = await devicePublicKey()
    const spki = fromBase64Url(exported)
    const imported = await crypto.subtle.importKey(
      'spki',
      spki,
      { name: 'ECDSA', namedCurve: 'P-256' },
      true,
      ['verify'],
    )
    expect(imported.type).toBe('public')
  })

  it('keeps the same key across calls, so a device stays the same device', async () => {
    const first = await devicePublicKey()
    expect(await devicePublicKey()).toBe(first)
  })

  it('signs a challenge in a way its own public key verifies', async () => {
    const challenge = 'a-challenge-from-the-server'
    const exported = await devicePublicKey()
    const signature = await signChallenge(challenge)

    const key = await crypto.subtle.importKey(
      'spki',
      fromBase64Url(exported),
      { name: 'ECDSA', namedCurve: 'P-256' },
      true,
      ['verify'],
    )
    const verified = await crypto.subtle.verify(
      { name: 'ECDSA', hash: 'SHA-256' },
      key,
      fromBase64Url(signature),
      new TextEncoder().encode(challenge),
    )
    expect(verified).toBe(true)
  })

  it('refuses a signature made for another challenge', async () => {
    const exported = await devicePublicKey()
    const signature = await signChallenge('the-real-one')
    const key = await crypto.subtle.importKey(
      'spki',
      fromBase64Url(exported),
      { name: 'ECDSA', namedCurve: 'P-256' },
      true,
      ['verify'],
    )
    const verified = await crypto.subtle.verify(
      { name: 'ECDSA', hash: 'SHA-256' },
      key,
      fromBase64Url(signature),
      new TextEncoder().encode('a-different-one'),
    )
    expect(verified).toBe(false)
  })

  it('produces a fresh key once the old one is forgotten', async () => {
    const first = await devicePublicKey()
    await forgetDeviceKey()
    expect(await devicePublicKey()).not.toBe(first)
  })
})
