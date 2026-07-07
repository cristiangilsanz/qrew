import { Elements, PaymentElement, useElements, useStripe } from '@stripe/react-stripe-js'
import { loadStripe } from '@stripe/stripe-js'
import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
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
      <Button type="submit" className="w-full" isLoading={loading} disabled={!stripe || !elements}>
        {t('tickets.payment.confirmButton')}
      </Button>
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
