import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import CashierDashboard from '../CashierDashboard'
import { ThemeProvider } from '../../contexts/ThemeContext'

jest.mock('../../api', () => ({ apiFetch: jest.fn() }))
jest.mock('../../components/InvoiceLink', () => () => null)
import * as api from '../../api'

describe('CashierDashboard', () => {
  beforeEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ json: () => Promise.resolve({ state: 'ok' }) }),
    )
    global.crypto = { randomUUID: () => 'test-key' }
    api.apiFetch.mockImplementation((url) => {
      if (url === '/orders') {
        return Promise.resolve({ json: () => Promise.resolve({ orders: [] }) })
      }
      if (url.startsWith('/invoices')) {
        return Promise.resolve({
          json: () => Promise.resolve({ invoices: [{ invoice_id: 1 }] }),
        })
      }
      return Promise.resolve({ json: () => Promise.resolve({}) })
    })
  })

  afterEach(() => {
    jest.restoreAllMocks()
    delete global.fetch
    delete global.crypto
  })

  test('shows legal links', async () => {
    render(
      <ThemeProvider>
        <CashierDashboard />
      </ThemeProvider>,
    )
    await screen.findByText(/Cashier Dashboard/)
    expect(screen.getByRole('link', { name: /terms/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /refund/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /contact/i })).toBeInTheDocument()
  })

  test('refund confirm flow', async () => {
    const refundSpy = api.apiFetch.mockImplementation((url, options) => {
      if (url === '/orders') {
        return Promise.resolve({ json: () => Promise.resolve({ orders: [] }) })
      }
      if (url.startsWith('/invoices')) {
        return Promise.resolve({
          json: () => Promise.resolve({ invoices: [{ invoice_id: 1 }] }),
        })
      }
      if (url === '/payments/1/refund') {
        return Promise.resolve({
          json: () => Promise.resolve({ data: { refunded: true } }),
        })
      }
      return Promise.resolve({ json: () => Promise.resolve({}) })
    })

    jest.spyOn(window, 'confirm').mockReturnValue(true)

    render(
      <ThemeProvider>
        <CashierDashboard />
      </ThemeProvider>,
    )

    const refundButton = await screen.findByRole('button', { name: /refund/i })
    fireEvent.click(refundButton)

    expect(window.confirm).toHaveBeenCalled()

    await waitFor(() => {
      expect(refundSpy).toHaveBeenCalledWith(
        '/payments/1/refund',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Idempotency-Key': expect.any(String),
          }),
        }),
      )
    })

    expect(await screen.findByText(/Key:/i)).toBeInTheDocument()
  })
})
