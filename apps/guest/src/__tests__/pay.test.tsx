import '@testing-library/jest-dom';
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PayPage } from '../pages/Pay';

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ orderId: '1' }),
  };
});

function renderPay() {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <PayPage />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe('pay page', () => {
  beforeEach(() => {
    jest.useRealTimers();
    // @ts-ignore
    global.fetch = jest.fn();
  });

  test('shows error message when invoice fetch fails', async () => {
    // @ts-ignore
    global.fetch.mockRejectedValueOnce(new Error('Network'));

    renderPay();

    const msg = await screen.findByText(/failed to load invoice/i);
    expect(msg).toBeInTheDocument();
  });

  test('UPI URL contains pa/pn/am', async () => {
    // @ts-ignore
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [],
        tax: 0,
        total: 55,
        upi: { pa: 'test@upi', pn: 'Test' },
        onlineUpi: true,
      }),
    });

    renderPay();
    const link = await screen.findByRole('link', { name: /gpay/i });
    const href = link.getAttribute('href')!;
    expect(href).toContain('pa=test@upi');
    expect(href).toContain('pn=Test');
    expect(href).toContain('am=55');
  });

  test('skip UTR still shows QR', async () => {
    const fetchMock = jest.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [],
        tax: 0,
        total: 55,
        upi: { pa: 't@upi', pn: 'T' },
        onlineUpi: true,
      }),
    });
    // @ts-ignore
    global.fetch = fetchMock;

    renderPay();
    await screen.findByText(/total/i);
    fireEvent.click(screen.getByRole('button', { name: /i've paid/i }));
    fireEvent.click(screen.getByRole('button', { name: /skip/i }));

    expect(screen.getByTestId('cashier-qr')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  test('posts utr and orderId', async () => {
    jest.useFakeTimers();
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [],
          tax: 0,
          total: 55,
          upi: { pa: 't@upi', pn: 'T' },
          onlineUpi: true,
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    // @ts-ignore
    global.fetch = fetchMock;

    renderPay();
    await screen.findByText(/total/i);
    fireEvent.click(screen.getByRole('button', { name: /i've paid/i }));
    fireEvent.change(screen.getByLabelText(/utr/i), {
      target: { value: '123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/orders/1/utr', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ orderId: '1', utr: '123' }),
    });
  });

  test('status poll switches to success', async () => {
    jest.useFakeTimers();
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [],
          tax: 0,
          total: 55,
          upi: { pa: 't@upi', pn: 'T' },
          onlineUpi: true,
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'pending' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'settled' }),
      });
    // @ts-ignore
    global.fetch = fetchMock;

    renderPay();
    await screen.findByText(/total/i);
    fireEvent.click(screen.getByRole('button', { name: /i've paid/i }));
    fireEvent.change(screen.getByLabelText(/utr/i), {
      target: { value: '123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() =>
      expect(screen.getByText(/waiting for verification/i)).toBeInTheDocument()
    );

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() =>
      expect(screen.getByText(/payment successful/i)).toBeInTheDocument()
    );
  });
});
