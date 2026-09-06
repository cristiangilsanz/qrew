// resolves the passkey ceremony on the native shell
import { Passkeys } from '@capawesome/capacitor-passkeys'

interface AuthenticationOptions {
  challenge: string
  rpId: string
  userVerification: string
  allowCredentials?: { id: string; type: 'public-key' }[]
}

// asks the platform for the credential the server named, falling back to any passkey of
// the domain when it holds none under that name, so a stale entry never blocks the holder
export async function getNativePasskey(options: AuthenticationOptions) {
  const base = {
    challenge: options.challenge,
    rpId: options.rpId,
    userVerification: options.userVerification as never,
  }
  const allowed = options.allowCredentials ?? []
  if (allowed.length === 0) return Passkeys.getPasskey(base)
  try {
    return await Passkeys.getPasskey({ ...base, allowCredentials: allowed })
  } catch (error) {
    console.warn('passkey allow list rejected', error)
    return Passkeys.getPasskey(base)
  }
}
