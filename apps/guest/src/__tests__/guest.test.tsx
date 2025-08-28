import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n, { setLanguage } from '../i18n';
import { CartPage } from '../pages/CartPage';
import { MenuPage } from '../pages/MenuPage';
import { useCartStore } from '../store/cart';

jest.mock(
  '@neo/ui',
  () => ({
    EmptyState: () => null,
    ShoppingCart: () => null,
    SkeletonList: () => null,
    Utensils: () => null,
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

function renderMenu() {
  const qc = new QueryClient();
  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={qc}>
        <BrowserRouter>
          <MenuPage />
        </BrowserRouter>
      </QueryClientProvider>
    </I18nextProvider>
  );
}

describe('guest flows', () => {
  beforeEach(() => {
    // @ts-ignore
    global.fetch = jest.fn();
    useCartStore.setState({ items: [] });
  });

  test('shows expired banner and disables order', async () => {
    // @ts-ignore
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'EXPIRED' }),
    });
    useCartStore.setState({ items: [{ id: '1', name: 'Test', qty: 1 }] });
    renderCart();
    await waitFor(() =>
      expect(screen.getByTestId('license-banner')).toBeInTheDocument()
    );
    expect(
      screen.getByRole('link', { name: /renew/i })
    ).toHaveAttribute('href', '/admin/billing');
    expect(
      screen.getByRole('button', { name: /place order/i })
    ).toBeDisabled();
  });

  test('shows grace banner and allows order', async () => {
    // @ts-ignore
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'GRACE' }),
    });
    useCartStore.setState({ items: [{ id: '1', name: 'Test', qty: 1 }] });
    renderCart();
    await waitFor(() =>
      expect(screen.getByTestId('license-banner')).toBeInTheDocument()
    );
    expect(
      screen.getByRole('button', { name: /place order/i })
    ).not.toBeDisabled();
  });

  test('menu disables add when expired', async () => {
    // @ts-ignore
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'EXPIRED' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          categories: [
            { id: 'c1', name_i18n: { en: 'Cat' }, items: [{ id: 'i1', name_i18n: { en: 'Item' } }] },
          ],
        }),
      });
    renderMenu();
    await waitFor(() => screen.getByText('Item'));
    expect(screen.getByRole('button', { name: '+' })).toBeDisabled();
  });

  test('i18n fallback and cookie', async () => {
    await i18n.changeLanguage('fr');
    expect(i18n.t('place_order')).toBe('Place order');
    setLanguage('es');
    expect(document.cookie).toMatch(/glang=es/);
  });
});
