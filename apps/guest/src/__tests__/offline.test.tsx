import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n from '../i18n';
import { MenuPage } from '../pages/MenuPage';
import { CartPage } from '../pages/CartPage';
import { Layout } from '../components/Layout';
import { useCartStore } from '../store/cart';
import { retryQueuedOrders } from '../queue';

jest.mock(
  '@neo/ui',
  () => ({
    EmptyState: () => null,
    Utensils: () => null,
    ShoppingCart: () => null,
    SkeletonList: () => null,
    toast: { error: jest.fn(), success: jest.fn() },
  }),
  { virtual: true }
);

jest.mock(
  '@neo/api',
  () => ({
    useLicense: jest.fn().mockReturnValue({}),
  }),
  { virtual: true }
);

const wrapper = (initial: string, node: React.ReactNode) => {
  const qc = new QueryClient();
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[initial]}>
          <Routes>
            <Route element={<Layout />}>{node}</Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  );
};

test('offline menu and queued order retry', async () => {
  Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
  localStorage.clear();
  (global.fetch as any) = jest.fn((url: string) => {
    if (url.startsWith('/status.json')) {
      return Promise.resolve(new Response('{}', { status: 200 }));
    }
    if (url === '/api/menu') {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            categories: [
              { id: 'c1', name_i18n: { en: 'Cat' }, items: [{ id: '1', name_i18n: { en: 'Tea' } }] },
            ],
          }),
          { status: 200 }
        )
      );
    }
    if (url === '/api/orders') {
      return Promise.reject(new TypeError('fail'));
    }
    return Promise.reject(new Error('unknown'));
  });

  wrapper('/menu', <Route path="/menu" element={<MenuPage />} />);
  await waitFor(() =>
    expect((global.fetch as jest.Mock).mock.calls.some((c) => c[0] === '/api/menu')).toBe(true)
  );

  useCartStore.setState({ items: [{ id: '1', name: 'Tea', qty: 1 }] });
  wrapper('/cart', <Route path="/cart" element={<CartPage />} />);
  fireEvent.click(screen.getByRole('button', { name: /place order/i }));
  await waitFor(() =>
    expect(screen.getByRole('button', { name: /queued/i })).toBeInTheDocument()
  );
  expect(JSON.parse(localStorage.getItem('queuedOrders')!).length).toBe(1);

  (global.fetch as jest.Mock).mockImplementation((url: string) => {
    if (url.startsWith('/status.json')) {
      return Promise.resolve(new Response('{}', { status: 200 }));
    }
    if (url === '/api/orders') {
      return Promise.resolve(
        new Response(JSON.stringify({ id: '42' }), { status: 200 })
      );
    }
    return Promise.reject(new Error('unknown'));
  });
  Object.defineProperty(navigator, 'onLine', { value: true });
  await retryQueuedOrders();
  expect((global.fetch as jest.Mock).mock.calls.pop()?.[0]).toBe('/api/orders');
});
