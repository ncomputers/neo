import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState, ShoppingCart } from '@neo/ui';
import { Header } from '../components/Header';
import { useCartStore } from '../store/cart';
import { useLicense } from '../hooks/useLicense';

export function CartPage() {
  const { t } = useTranslation();
  const { items, clear, add } = useCartStore();
  const { data } = useLicense();
  const [tip, setTip] = useState(0);

  const expired = data?.status === 'EXPIRED';

  return (
    <div>
      <Header />
      <h1>{t('cart')}</h1>
      {expired && (
        <div data-testid="license-banner">{t('license_expired')}</div>
      )}
      {items.length === 0 ? (
        <EmptyState
          message={t('empty_cart')}
          icon={<ShoppingCart className="w-12 h-12 mx-auto" />}
        />
      ) : (
        <>
          <ul>
            {items.map((it) => (
              <li key={it.id}>
                {it.name} x {it.qty}
                <button
                  aria-label="decrease"
                  onClick={() => add({ id: it.id, name: it.name, qty: -1 })}
                >
                  -
                </button>
                <button
                  aria-label="increase"
                  onClick={() => add({ id: it.id, name: it.name, qty: 1 })}
                >
                  +
                </button>
              </li>
            ))}
          </ul>
          <label>
            {t('tip')}:
            <input
              type="number"
              value={tip}
              onChange={(e) => setTip(Number(e.target.value))}
            />
          </label>
          <button disabled={expired} onClick={() => clear()}>
            {t('place_order')}
          </button>
        </>
      )}
    </div>
  );
}
