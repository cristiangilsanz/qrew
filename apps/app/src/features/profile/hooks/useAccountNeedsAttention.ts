// reports whether the account has something outstanding worth flagging in the interface
import { useProfile } from './useProfile'

// tells the dock and the profile list to mark the account until its identity check settles
export function useAccountNeedsAttention(): boolean {
  const { data: profile } = useProfile()
  if (!profile) return false
  return profile.kyc_status !== 'approved'
}
