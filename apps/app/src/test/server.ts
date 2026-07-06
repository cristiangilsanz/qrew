import { setupServer } from 'msw/node'

import { authHandlers } from './handlers/auth'
import { catalogHandlers } from './handlers/catalog'

export const server = setupServer(...authHandlers, ...catalogHandlers)
