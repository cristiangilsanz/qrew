import { Network } from '@capacitor/network'
import { useEffect, useState } from 'react'

export function useNetwork() {
  const [isOnline, setIsOnline] = useState(true)

  useEffect(() => {
    Network.getStatus().then((status) => setIsOnline(status.connected))

    const listener = Network.addListener('networkStatusChange', (status) => {
      setIsOnline(status.connected)
    })

    return () => {
      listener.then((l) => l.remove())
    }
  }, [])

  return { isOnline }
}
