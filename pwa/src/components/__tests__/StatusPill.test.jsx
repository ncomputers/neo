import { render, screen, waitFor } from '@testing-library/react'
import StatusPill from '../StatusPill'

describe('StatusPill', () => {
  const mockFetch = (state) => {
    global.fetch = jest.fn().mockResolvedValue({
      json: async () => ({ state }),
    })
  }

  it.each([
    ['ok', 'bg-green-500'],
    ['degraded', 'bg-amber-500'],
    ['outage', 'bg-red-500'],
  ])('renders %s color', async (status, cls) => {
    mockFetch(status)
    render(<StatusPill />)
    const pill = await screen.findByTestId('status-pill')
    await waitFor(() => expect(pill.className).toContain(cls))
  })
})
