import { setupServer } from 'msw/node'

import { authHandlers } from './handlers/auth'
import { catalogHandlers } from './handlers/catalog'
import { paymentsHandlers } from './handlers/payments'
import { salesHandlers } from './handlers/sales'

export const server = setupServer(
  ...authHandlers,
  ...catalogHandlers,
  ...salesHandlers,
  ...paymentsHandlers,
)
