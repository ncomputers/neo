import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import { EmptyState, ShoppingCart, toast } from '@neo/ui';
import { Header } from '../components/Header';
import { useCartStore } from '../store/cart';
import { useLicenseStatus } from '@neo/api';
import { CartSkeleton } from '../components/CartSkeleton';

export function CartPage() {
  const { t } = useTranslation();
  const { items, clear } = useCartStore();
  const { data, isPending, isError } = useLicenseStatus({
    onError: () => toast.error(t('error_cart')),
  });
  const [tip, setTip] = useState(0);

  const expired = data?.status === 'EXPIRED';
  const { mutate, isPending: isOrdering } = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items, tip }),
      });
      if (!res.ok) throw new Error('order');
      return res.json();
    },
    onSuccess: () => clear(),
    onError: () => toast.error(t('error_order')),
  });

  return (
    <div>
      <Header />
      <h1>{t('cart')}</h1>
      {isPending ? (
        <CartSkeleton />
      ) : isError ? (
        <EmptyState
          message={t('error_cart')}
          icon={<ShoppingCart className="w-12 h-12 mx-auto" />}
        />
      ) : items.length === 0 ? (
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
          <button
            disabled={expired || isOrdering}
            onClick={() => mutate()}
          >
            {t('place_order')}
          </button>
        </>
      )}
    </div>
  );
}
