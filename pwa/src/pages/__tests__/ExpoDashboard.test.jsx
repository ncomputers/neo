import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { apiFetch } from '../../api'
import ExpoDashboard from '../ExpoDashboard'

jest.mock('../../api', () => ({ apiFetch: jest.fn() }))
jest.mock('../../contexts/ThemeContext', () => ({
  useTheme: () => ({ logo: null }),
}))

const sampleOrders = [
  { order_id: 1, table: '1', age_s: 30, allergen_badges: [] },
  { order_id: 2, table: '2', age_s: 45, allergen_badges: [] },
]

describe('ExpoDashboard hotkeys', () => {
  beforeEach(() => {
    apiFetch.mockReset()
    apiFetch
      .mockResolvedValueOnce({ json: async () => ({ tickets: sampleOrders }) })
      .mockResolvedValueOnce({ json: async () => ({}) })
      .mockResolvedValueOnce({
        json: async () => ({ tickets: [sampleOrders[0]] }),
      })
  })

  it('pressing P picks last order', async () => {
    render(<ExpoDashboard />)
    await screen.findByText('Table 1')
    await screen.findByText('Table 2')

    fireEvent.keyDown(window, { key: 'P' })

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith('/kds/expo/2/picked', {
        method: 'POST',
      }),
    )
    await waitFor(() =>
      expect(screen.queryByText('Table 2')).not.toBeInTheDocument(),
    )
  })
})
