import { zodResolver } from '@hookform/resolvers/zod'
import { AnimatePresence, motion } from 'framer-motion'
import { Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'

import { useDeleteAccount } from '../hooks/useDeleteAccount'

const schema = z.object({ current_password: z.string().min(1) })
type Values = z.infer<typeof schema>

const darkInput =
  'border-white/5 bg-black/30 text-white/70 placeholder:text-white/15 focus-visible:border-white/15 focus-visible:ring-0 focus-visible:ring-offset-0'

const COUNTDOWN = 10

export function DeleteAccountDialog() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [seconds, setSeconds] = useState(COUNTDOWN)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { current_password: '' },
  })

  const deleteAccount = useDeleteAccount()

  const openModal = () => {
    setSeconds(COUNTDOWN)
    setOpen(true)
  }

  const closeModal = () => {
    setOpen(false)
    form.reset()
    if (timerRef.current) clearInterval(timerRef.current)
  }

  useEffect(() => {
    if (!open) return
    timerRef.current = setInterval(() => {
      setSeconds((s) => {
        if (s <= 1) {
          clearInterval(timerRef.current!)
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [open])

  return (
    <>
      <button
        onClick={openModal}
        className="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-white/5"
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-500/10">
          <Trash2 className="h-4 w-4 text-red-400" />
        </div>
        <span className="flex-1 text-sm font-semibold text-red-400">
          {t('profile.deleteAccount.button')}
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && closeModal()}
          >
            <motion.div
              initial={{ y: 32, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 32, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className="w-full max-w-sm rounded-2xl border border-red-500/20 bg-[#111] p-6"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10">
                  <Trash2 className="h-5 w-5 text-red-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-red-400">
                    {t('profile.deleteAccount.button')}
                  </h3>
                  <p className="text-muted-foreground text-xs">
                    {t('profile.deleteAccount.irreversible')}
                  </p>
                </div>
              </div>

              <p className="text-muted-foreground mb-5 text-sm">
                {t('profile.deleteAccount.description')}
              </p>

              <Form {...form}>
                <form
                  onSubmit={form.handleSubmit((v) => deleteAccount.mutate(v.current_password))}
                  className="space-y-4"
                >
                  <FormField
                    control={form.control}
                    name="current_password"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-muted-foreground text-xs">
                          {t('profile.deleteAccount.currentPassword')}
                        </FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            autoComplete="current-password"
                            className={darkInput}
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="flex items-center justify-between pt-1">
                    <button
                      type="button"
                      className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
                      onClick={closeModal}
                    >
                      {t('common.goBack')}
                    </button>
                    <button
                      type="submit"
                      disabled={seconds > 0 || deleteAccount.isPending}
                      className="flex h-10 min-w-[112px] items-center justify-center gap-2 rounded-full bg-red-500 px-5 text-sm font-semibold text-white disabled:opacity-50"
                    >
                      {deleteAccount.isPending ? (
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      ) : seconds > 0 ? (
                        `Wait ${seconds}s`
                      ) : (
                        <>
                          <Trash2 className="h-3.5 w-3.5" />
                          {t('profile.deleteAccount.confirm')}
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </Form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
