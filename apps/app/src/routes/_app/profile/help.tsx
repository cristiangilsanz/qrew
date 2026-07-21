import { createFileRoute } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import { Bug, ChevronRight, HelpCircle, MessageCircle } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/profile/help')({
  component: HelpPage,
})

const expandVariants = {
  hidden: { height: 0, opacity: 0 },
  visible: { height: 'auto', opacity: 1, transition: { duration: 0.25, ease: [0.4, 0, 0.2, 1] } },
  exit: { height: 0, opacity: 0, transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] } },
}

function FaqRow({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-4 text-left"
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
          <HelpCircle className="text-muted-foreground h-4 w-4" />
        </div>
        <span className="flex-1 text-sm font-medium">{question}</span>
        <ChevronRight
          className={cn(
            'text-muted-foreground h-4 w-4 shrink-0 transition-transform duration-200',
            open && 'text-primary rotate-90',
          )}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            variants={expandVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            style={{ overflow: 'hidden' }}
          >
            <div className="border-t border-white/10 bg-white/[0.03] px-4 pt-3 pb-4">
              <p className="text-muted-foreground text-justify text-sm leading-relaxed">{answer}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

function HelpPage() {
  const { t } = useTranslation()
  const iconClass = 'h-4 w-4 text-muted-foreground'

  const faqItems = [
    { q: t('profile.help.faq.q1'), a: t('profile.help.faq.a1') },
    { q: t('profile.help.faq.q2'), a: t('profile.help.faq.a2') },
    { q: t('profile.help.faq.q3'), a: t('profile.help.faq.a3') },
  ]

  return (
    <div className="min-h-screen px-4 pt-4 pb-28">
      <BackButton to="/profile" className="mb-6" />
      <h1 className="mb-6 text-xl font-bold">{t('profile.help.title')}</h1>

      <p className="text-muted-foreground mb-3 px-1 text-xs font-semibold tracking-wider uppercase">
        {t('profile.help.faqSection')}
      </p>
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        {faqItems.map((item, i) => (
          <div key={i}>
            {i > 0 && <div className="mx-4 border-t border-white/10" />}
            <FaqRow question={item.q} answer={item.a} />
          </div>
        ))}
      </div>

      <p className="text-muted-foreground mt-6 mb-3 px-1 text-xs font-semibold tracking-wider uppercase">
        {t('profile.help.contactSection')}
      </p>
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <a
          href="mailto:support@qrew.dev"
          className="flex items-center gap-3 px-4 py-4 transition-colors hover:bg-white/5"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
            <MessageCircle className={iconClass} />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium">{t('profile.help.contactSupport')}</p>
            <p className="text-muted-foreground text-xs">{t('profile.help.contactSupportDesc')}</p>
          </div>
          <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
        </a>

        <div className="mx-4 border-t border-white/10" />

        <a
          href="https://github.com/cristiangilsanz/qrew/issues"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 px-4 py-4 transition-colors hover:bg-white/5"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
            <Bug className={iconClass} />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium">{t('profile.help.reportBug')}</p>
            <p className="text-muted-foreground text-xs">{t('profile.help.reportBugDesc')}</p>
          </div>
          <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
        </a>
      </div>
    </div>
  )
}
