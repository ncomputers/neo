import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n, { setLanguage } from '../i18n';
import { CartPage } from '../pages/CartPage';
import { useCartStore } from '../store/cart';
import { Layout } from '../components/Layout';

jest.mock('../analytics', () => ({
  enableAnalytics: jest.fn(),
  disableAnalytics: jest.fn(),
  hasAnalyticsConsent: jest.fn(() => false),
  initAnalytics: jest.fn(),
}));

jest.mock(
  '@neo/utils',
  () => ({
    capturePageView: jest.fn(),
  }),
  { virtual: true },
);

jest.mock(
  '@neo/ui',
  () => ({
    EmptyState: () => null,
    ShoppingCart: () => null,
    SkeletonList: () => null,
    LicenseBanner: ({ status, daysLeft }: any) => (
      <div>{status === 'EXPIRED' ? 'License expired' : `Subscription ends in ${daysLeft} days`}</div>
    ),
    CookieBanner: () => null,
    toast: { error: jest.fn() },
  }),
  { virtual: true }
);

jest.mock(
  '@neo/api',
  () => ({
    useLicense: jest.fn(),
  }),
  { virtual: true }
);

function renderCart() {
  const qc = new QueryClient();
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/']}> 
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<CartPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  );
}

describe('guest flows', () => {
  beforeEach(() => {
    const api: any = require('@neo/api');
    api.useLicense.mockReturnValue({ data: { status: 'EXPIRED' } });
    useCartStore.setState({ items: [] });
  });

  test('EXPIRED disables order', async () => {
    useCartStore.setState({ items: [{ id: '1', name: 'Test', qty: 1 }] });
    renderCart();
    await waitFor(() =>
      expect(screen.getByText('License expired')).toBeInTheDocument()
    );
    expect(screen.getByRole('button', { name: /place order/i })).toBeDisabled();
  });

  test('GRACE shows banner but allows order', async () => {
    const api: any = require('@neo/api');
    api.useLicense.mockReturnValue({ data: { status: 'GRACE', daysLeft: 3 } });
    useCartStore.setState({ items: [{ id: '1', name: 'Test', qty: 1 }] });
    renderCart();
    await waitFor(() =>
      expect(
        screen.getByText(/Subscription ends in 3 days/)
      ).toBeInTheDocument()
    );
    expect(screen.getByRole('button', { name: /place order/i })).not.toBeDisabled();
  });

  test('i18n fallback and cookie', async () => {
    await i18n.changeLanguage('fr');
    expect(i18n.t('place_order')).toBe('Place order');
    setLanguage('es');
    expect(document.cookie).toMatch(/glang=es/);
  });
});
