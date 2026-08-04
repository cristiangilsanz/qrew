import { createFileRoute } from '@tanstack/react-router'
import { type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'

export const Route = createFileRoute('/_app/profile/terms')({
  component: TermsPage,
})

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="mb-3 text-base font-bold text-gray-900">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-gray-600">{children}</div>
    </section>
  )
}

function TermsEN() {
  return (
    <>
      <Section title="1. Acceptance of Terms">
        <p className="text-justify">
          By accessing or using Qrew, you agree to be bound by these Terms of Service. If you do not
          agree with any part of these terms, you may not use our service.
        </p>
      </Section>
      <Section title="2. Use of the Service">
        <p className="text-justify">
          Qrew provides a platform for discovering and purchasing tickets to events. You agree to
          use the service only for lawful purposes and in accordance with these terms.
        </p>
        <p className="text-justify">
          You are responsible for maintaining the confidentiality of your account credentials and
          for all activity that occurs under your account.
        </p>
      </Section>
      <Section title="3. Tickets and Purchases">
        <p className="text-justify">
          All ticket purchases are final unless the event is cancelled or rescheduled by the
          organiser. Tickets are non-transferable and linked to the account used to purchase them.
        </p>
        <p className="text-justify">
          Qrew acts as an intermediary between buyers and event organisers. We are not responsible
          for the conduct, content, or cancellation of any event.
        </p>
      </Section>
      <Section title="4. Refunds and Cancellations">
        <p className="text-justify">
          Refund eligibility is determined by the event organiser&apos;s refund policy, which is
          shown at the time of purchase. In the event of a cancellation by the organiser, a full
          refund will be issued to the original payment method.
        </p>
        <p className="text-justify">
          If you believe you are entitled to a refund, contact our support team with your order
          details.
        </p>
      </Section>
      <Section title="5. User Accounts">
        <p className="text-justify">
          You must be at least 18 years old to create an account and purchase tickets. You agree to
          provide accurate and complete information when registering.
        </p>
        <p className="text-justify">
          We reserve the right to suspend or terminate accounts that violate these terms or engage
          in fraudulent activity.
        </p>
      </Section>
      <Section title="6. Intellectual Property">
        <p className="text-justify">
          All content, trademarks, and intellectual property on Qrew are owned by or licensed to us.
          You may not reproduce, distribute, or create derivative works without our prior written
          permission.
        </p>
      </Section>
      <Section title="7. Limitation of Liability">
        <p className="text-justify">
          To the fullest extent permitted by law, Qrew shall not be liable for any indirect,
          incidental, or consequential damages arising from your use of the service.
        </p>
      </Section>
      <Section title="8. Changes to These Terms">
        <p className="text-justify">
          We may update these Terms of Service from time to time. We will notify you of significant
          changes by updating the date at the top of this page. Continued use of the service after
          changes constitutes acceptance of the new terms.
        </p>
      </Section>
      <Section title="9. Contact">
        <p className="text-justify">
          If you have any questions about these terms, please contact us at support@qrew.dev.
        </p>
      </Section>
    </>
  )
}

function TermsES() {
  return (
    <>
      <Section title="1. Aceptación de los Términos">
        <p className="text-justify">
          Al acceder o utilizar Qrew, aceptas quedar vinculado por estos Términos de Servicio. Si no
          estás de acuerdo con alguna parte de estos términos, no podrás utilizar nuestro servicio.
        </p>
      </Section>
      <Section title="2. Uso del Servicio">
        <p className="text-justify">
          Qrew proporciona una plataforma para descubrir y comprar entradas a eventos. Aceptas
          utilizar el servicio únicamente con fines legales y de acuerdo con estos términos.
        </p>
        <p className="text-justify">
          Eres responsable de mantener la confidencialidad de las credenciales de tu cuenta y de
          toda la actividad que ocurra bajo tu cuenta.
        </p>
      </Section>
      <Section title="3. Entradas y Compras">
        <p className="text-justify">
          Todas las compras de entradas son definitivas, salvo que el evento sea cancelado o
          reprogramado por el organizador. Las entradas son intransferibles y están vinculadas a la
          cuenta utilizada para adquirirlas.
        </p>
        <p className="text-justify">
          Qrew actúa como intermediario entre compradores y organizadores de eventos. No somos
          responsables de la conducta, el contenido ni la cancelación de ningún evento.
        </p>
      </Section>
      <Section title="4. Reembolsos y Cancelaciones">
        <p className="text-justify">
          La elegibilidad para el reembolso se determina según la política de reembolso del
          organizador del evento, que se muestra en el momento de la compra. En caso de cancelación
          por parte del organizador, se emitirá un reembolso completo al método de pago original.
        </p>
        <p className="text-justify">
          Si crees que tienes derecho a un reembolso, contacta con nuestro equipo de soporte con los
          detalles de tu pedido.
        </p>
      </Section>
      <Section title="5. Cuentas de Usuario">
        <p className="text-justify">
          Debes tener al menos 18 años para crear una cuenta y comprar entradas. Aceptas
          proporcionar información precisa y completa al registrarte.
        </p>
        <p className="text-justify">
          Nos reservamos el derecho de suspender o cancelar cuentas que incumplan estos términos o
          participen en actividades fraudulentas.
        </p>
      </Section>
      <Section title="6. Propiedad Intelectual">
        <p className="text-justify">
          Todo el contenido, las marcas comerciales y la propiedad intelectual de Qrew son propiedad
          de nosotros o están licenciados por nosotros. No puedes reproducir, distribuir ni crear
          obras derivadas sin nuestro permiso previo por escrito.
        </p>
      </Section>
      <Section title="7. Limitación de Responsabilidad">
        <p className="text-justify">
          En la máxima medida permitida por la ley, Qrew no será responsable de ningún daño
          indirecto, incidental o consecuente que surja del uso del servicio.
        </p>
      </Section>
      <Section title="8. Cambios en Estos Términos">
        <p className="text-justify">
          Podemos actualizar estos Términos de Servicio de vez en cuando. Te notificaremos los
          cambios significativos actualizando la fecha en la parte superior de esta página. El uso
          continuado del servicio tras los cambios constituye la aceptación de los nuevos términos.
        </p>
      </Section>
      <Section title="9. Contacto">
        <p className="text-justify">
          Si tienes alguna pregunta sobre estos términos, contáctanos en support@qrew.dev.
        </p>
      </Section>
    </>
  )
}

function TermsPage() {
  const { i18n } = useTranslation()
  const isES = i18n.language.startsWith('es')

  return (
    <div className="min-h-screen bg-white px-6 pt-6 pb-28">
      <BackButton to="/profile/about" className="mb-8" />

      <h1 className="mb-2 text-2xl font-bold text-gray-900">
        {isES ? 'Términos de Servicio' : 'Terms of Service'}
      </h1>
      <p className="mb-10 text-xs text-gray-400">
        {isES ? 'Última actualización: enero 2025' : 'Last updated: January 2025'}
      </p>

      {isES ? <TermsES /> : <TermsEN />}
    </div>
  )
}
