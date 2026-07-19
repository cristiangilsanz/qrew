import { Elements, PaymentElement, useElements, useStripe } from '@stripe/react-stripe-js'
import { loadStripe } from '@stripe/stripe-js'
import { CreditCard } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { env } from '@/config/env'

const stripePromise = loadStripe(env.STRIPE_PUBLISHABLE_KEY)

interface FormProps {
  onSuccess: () => void
}

function PaymentForm({ onSuccess }: FormProps) {
  const { t } = useTranslation()
  const stripe = useStripe()
  const elements = useElements()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!stripe || !elements) return

    setLoading(true)
    setError(null)

    const result = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: `${window.location.origin}/tickets` },
      redirect: 'if_required',
    })

    if (result.error) {
      setError(result.error.message ?? t('tickets.payment.failed'))
      setLoading(false)
      return
    }

    if (result.paymentIntent?.status === 'succeeded') {
      onSuccess()
    }
    setLoading(false)
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
      <PaymentElement />
      {error && <p className="text-destructive text-sm">{error}</p>}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={loading || !stripe || !elements}
          className="bg-primary flex h-12 items-center gap-2 rounded-full px-6 text-sm font-semibold text-white shadow-lg disabled:opacity-50"
        >
          {loading ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : (
            <CreditCard className="h-4 w-4" />
          )}
          {t('tickets.payment.confirmButton')}
        </button>
      </div>
    </form>
  )
}

interface Props {
  clientSecret: string
  onSuccess: () => void
}

export function StripeCheckout({ clientSecret, onSuccess }: Props) {
  return (
    <Elements stripe={stripePromise} options={{ clientSecret, appearance: { theme: 'stripe' } }}>
      <PaymentForm onSuccess={onSuccess} />
    </Elements>
  )
}
