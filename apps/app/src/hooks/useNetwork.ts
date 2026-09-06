// provides use network
import { Network } from '@capacitor/network'
import { useEffect, useState } from 'react'

// provides use network
export function useNetwork() {
  const [isOnline, setIsOnline] = useState(true)

  useEffect(() => {
    Network.getStatus().then((status) => setIsOnline(status.connected))

    // implements listener
    const listener = Network.addListener('networkStatusChange', (status) => {
      setIsOnline(status.connected)
    })

    return () => {
      listener.then((l) => l.remove())
    }
  }, [])

  return { isOnline }
}
