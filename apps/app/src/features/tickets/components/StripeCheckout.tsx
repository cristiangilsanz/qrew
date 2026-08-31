// renders the stripe checkout component
import { Elements, PaymentElement, useElements, useStripe } from '@stripe/react-stripe-js'
import { loadStripe } from '@stripe/stripe-js'
import { CreditCard } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { env } from '@/config/env'

const stripePromise = env.STRIPE_PUBLISHABLE_KEY ? loadStripe(env.STRIPE_PUBLISHABLE_KEY) : null

interface FormProps {
  onSuccess: () => void
}

// renders the payment form component
function PaymentForm({ onSuccess }: FormProps) {
  const { t } = useTranslation()
  const stripe = useStripe()
  const elements = useElements()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // handles handle submit
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
      setError(t('tickets.payment.failed'))
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
          className="bg-primary hover:bg-primary/90 flex h-14 shrink-0 items-center gap-2 rounded-full px-5 text-sm font-semibold text-white shadow-lg transition disabled:opacity-40"
        >
          <CreditCard className="h-4 w-4" />
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

// renders the stripe checkout component
export function StripeCheckout({ clientSecret, onSuccess }: Props) {
  const { t } = useTranslation()

  if (!stripePromise) {
    return (
      <p className="text-muted-foreground py-6 text-center text-sm">
        {t('tickets.payment.unavailable')}
      </p>
    )
  }

  return (
    <Elements stripe={stripePromise} options={{ clientSecret, appearance: { theme: 'stripe' } }}>
      <PaymentForm onSuccess={onSuccess} />
    </Elements>
  )
}
