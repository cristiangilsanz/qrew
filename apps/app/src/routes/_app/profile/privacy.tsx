import { createFileRoute } from '@tanstack/react-router'
import { type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'

export const Route = createFileRoute('/_app/profile/privacy')({
  component: PrivacyPage,
})

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="mb-3 text-base font-bold text-gray-900">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-gray-600">{children}</div>
    </section>
  )
}

function PrivacyEN() {
  return (
    <>
      <Section title="1. Introduction">
        <p className="text-justify">
          Qrew is committed to protecting your personal data. This Privacy Policy explains what
          information we collect, how we use it, and your rights in relation to it.
        </p>
      </Section>
      <Section title="2. Data We Collect">
        <p className="text-justify">
          When you create an account and use Qrew, we collect information you provide directly,
          including your full name, email address, phone number, and payment details processed
          securely through our payment provider.
        </p>
        <p className="text-justify">
          We also collect data automatically when you use the app, such as device information, IP
          addresses, and usage activity for security and fraud prevention purposes.
        </p>
      </Section>
      <Section title="3. How We Use Your Data">
        <p className="text-justify">
          We use your data to operate the service, process ticket purchases, send booking
          confirmations, and provide customer support.
        </p>
        <p className="text-justify">
          We may also use your data to improve the app experience, detect fraud, and comply with
          legal obligations. We do not sell your personal data to third parties.
        </p>
      </Section>
      <Section title="4. Data Sharing">
        <p className="text-justify">
          We share your data with event organisers only to the extent necessary to fulfil your
          ticket purchase. We also share data with trusted service providers such as payment
          processors and cloud infrastructure providers, under strict confidentiality agreements.
        </p>
      </Section>
      <Section title="5. Data Retention">
        <p className="text-justify">
          We retain your personal data for as long as your account is active or as needed to provide
          the service. You may request deletion of your account and associated data at any time from
          the profile settings.
        </p>
      </Section>
      <Section title="6. Your Rights">
        <p className="text-justify">
          Depending on your location, you may have the right to access, correct, or delete your
          personal data, as well as the right to object to or restrict certain processing. To
          exercise these rights, contact us at support@qrew.dev.
        </p>
      </Section>
      <Section title="7. Security">
        <p className="text-justify">
          We take security seriously and implement appropriate technical and organisational measures
          to protect your data. All authentication is secured with passkeys and encrypted
          credentials.
        </p>
      </Section>
      <Section title="8. Changes to This Policy">
        <p className="text-justify">
          We may update this Privacy Policy from time to time. We will notify you of significant
          changes by updating the date at the top of this page.
        </p>
      </Section>
      <Section title="9. Contact">
        <p className="text-justify">
          For any privacy-related questions or requests, please contact us at support@qrew.dev.
        </p>
      </Section>
    </>
  )
}

function PrivacyES() {
  return (
    <>
      <Section title="1. Introducción">
        <p className="text-justify">
          Qrew se compromete a proteger tus datos personales. Esta Política de Privacidad explica
          qué información recopilamos, cómo la utilizamos y cuáles son tus derechos al respecto.
        </p>
      </Section>
      <Section title="2. Datos que Recopilamos">
        <p className="text-justify">
          Cuando creas una cuenta y utilizas Qrew, recopilamos la información que proporcionas
          directamente, incluyendo tu nombre completo, dirección de correo electrónico, número de
          teléfono y los datos de pago procesados de forma segura a través de nuestro proveedor de
          pagos.
        </p>
        <p className="text-justify">
          También recopilamos datos automáticamente cuando utilizas la aplicación, como información
          del dispositivo, direcciones IP y actividad de uso con fines de seguridad y prevención del
          fraude.
        </p>
      </Section>
      <Section title="3. Cómo Usamos tus Datos">
        <p className="text-justify">
          Utilizamos tus datos para operar el servicio, procesar la compra de entradas, enviar
          confirmaciones de reserva y proporcionar atención al cliente.
        </p>
        <p className="text-justify">
          También podemos usar tus datos para mejorar la experiencia de la aplicación, detectar
          fraudes y cumplir con las obligaciones legales. No vendemos tus datos personales a
          terceros.
        </p>
      </Section>
      <Section title="4. Compartición de Datos">
        <p className="text-justify">
          Compartimos tus datos con los organizadores de eventos solo en la medida necesaria para
          completar tu compra de entradas. También compartimos datos con proveedores de servicios de
          confianza, como procesadores de pagos y proveedores de infraestructura en la nube, bajo
          estrictos acuerdos de confidencialidad.
        </p>
      </Section>
      <Section title="5. Retención de Datos">
        <p className="text-justify">
          Conservamos tus datos personales mientras tu cuenta esté activa o mientras sea necesario
          para prestar el servicio. Puedes solicitar la eliminación de tu cuenta y los datos
          asociados en cualquier momento desde la configuración del perfil.
        </p>
      </Section>
      <Section title="6. Tus Derechos">
        <p className="text-justify">
          Según tu ubicación, puedes tener derecho a acceder, corregir o eliminar tus datos
          personales, así como el derecho a oponerte o restringir ciertos tratamientos. Para ejercer
          estos derechos, contáctanos en support@qrew.dev.
        </p>
      </Section>
      <Section title="7. Seguridad">
        <p className="text-justify">
          Nos tomamos la seguridad en serio e implementamos medidas técnicas y organizativas
          adecuadas para proteger tus datos. Toda la autenticación está protegida con passkeys y
          credenciales cifradas.
        </p>
      </Section>
      <Section title="8. Cambios en Esta Política">
        <p className="text-justify">
          Podemos actualizar esta Política de Privacidad de vez en cuando. Te notificaremos los
          cambios significativos actualizando la fecha en la parte superior de esta página.
        </p>
      </Section>
      <Section title="9. Contacto">
        <p className="text-justify">
          Para cualquier pregunta o solicitud relacionada con la privacidad, contáctanos en
          support@qrew.dev.
        </p>
      </Section>
    </>
  )
}

function PrivacyPage() {
  const { i18n } = useTranslation()
  const isES = i18n.language.startsWith('es')

  return (
    <div className="min-h-screen bg-white px-6 pt-6 pb-28">
      <BackButton to="/profile/about" className="mb-8" />

      <h1 className="mb-2 text-2xl font-bold text-gray-900">
        {isES ? 'Política de Privacidad' : 'Privacy Policy'}
      </h1>
      <p className="mb-10 text-xs text-gray-400">
        {isES ? 'Última actualización: enero 2025' : 'Last updated: January 2025'}
      </p>

      {isES ? <PrivacyES /> : <PrivacyEN />}
    </div>
  )
}
