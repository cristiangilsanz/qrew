import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

import logo from '@/assets/brand/logo.webp'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface AuthLayoutProps {
  title: string
  subtitle?: string
  children: ReactNode
}

export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-start px-4 pt-12">
      <div className="w-full max-w-sm space-y-2">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="text-center"
        >
          <img src={logo} alt="Qrew" className="mx-auto w-64" />
        </motion.div>

        <motion.div
          className="-mt-4"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.05 }}
        >
          <Card>
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-xl">{title}</CardTitle>
              {subtitle && <CardDescription>{subtitle}</CardDescription>}
            </CardHeader>
            <CardContent>{children}</CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}
