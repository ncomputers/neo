import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n, { setLanguage } from '../i18n';
import { CartPage } from '../pages/CartPage';
import { useCartStore } from '../store/cart';

jest.mock(
  '@neo/ui',
  () => ({
    EmptyState: () => null,
    ShoppingCart: () => null,
    SkeletonList: () => null,
    toast: { error: jest.fn() },
    useTheme: () => ({ logoURL: '' }),
    ThemeProvider: ({ children }: any) => children,
  }),
  { virtual: true }
);

function renderCart() {
  const qc = new QueryClient();
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={qc}>
        <BrowserRouter>
          <CartPage />
        </BrowserRouter>
      </QueryClientProvider>
    </I18nextProvider>
  );
}

describe('guest flows', () => {
  beforeEach(() => {
    // @ts-ignore
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'EXPIRED' }),
    });
    useCartStore.setState({ items: [] });
  });

  test('shows license banner and disables order', async () => {
    useCartStore.setState({ items: [{ id: '1', name: 'Test', qty: 1 }] });
    renderCart();
    await waitFor(() =>
      expect(screen.getByTestId('license-banner')).toBeInTheDocument()
    );
    expect(
      screen.getByRole('button', { name: /place order/i })
    ).toBeDisabled();
  });

  test('i18n fallback and cookie', async () => {
    await i18n.changeLanguage('fr');
    expect(i18n.t('place_order')).toBe('Place order');
    setLanguage('es');
    expect(document.cookie).toMatch(/glang=es/);
  });
});
