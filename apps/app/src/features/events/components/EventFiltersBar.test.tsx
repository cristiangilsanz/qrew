import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { EventFiltersBar } from './EventFiltersBar'

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    eventsApi: {
      ...actual.eventsApi,
      list: vi.fn().mockResolvedValue({ items: [], next_cursor: null }),
    },
  }
})

function renderBar(onFiltersChange = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return {
    onFiltersChange,
    ...render(
      <QueryClientProvider client={queryClient}>
        <EventFiltersBar onFiltersChange={onFiltersChange} />
      </QueryClientProvider>,
    ),
  }
}

describe('EventFiltersBar', () => {
  it('renders search input', () => {
    renderBar()
    expect(screen.getByPlaceholderText('Search events…')).toBeInTheDocument()
  })

  it('calls onFiltersChange with q on Enter', async () => {
    const { onFiltersChange } = renderBar()
    const input = screen.getByPlaceholderText('Search events…')
    await userEvent.type(input, 'Barcelona')
    await userEvent.keyboard('{Enter}')
    expect(onFiltersChange).toHaveBeenCalledWith(expect.objectContaining({ q: 'Barcelona' }))
  })

  it('clears search when X button clicked', async () => {
    const { onFiltersChange } = renderBar()
    const input = screen.getByPlaceholderText('Search events…')
    await userEvent.type(input, 'test')
    const clearBtn = screen.getByRole('button')
    await userEvent.click(clearBtn)
    expect(input).toHaveValue('')
    expect(onFiltersChange).toHaveBeenLastCalledWith({})
  })

  it('renders date input', () => {
    const { container } = renderBar()
    expect(container.querySelector('input[type="date"]')).toBeInTheDocument()
  })
})
