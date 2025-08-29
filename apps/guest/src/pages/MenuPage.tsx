import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Header } from '../components/Header';
import { EmptyState, Utensils, toast } from '@neo/ui';
import { MenuSkeleton } from '../components/MenuSkeleton';
import { useCartStore } from '../store/cart';

interface Item {
  id: string;
  name_i18n: Record<string, string>;
}
interface Category {
  id: string;
  name_i18n: Record<string, string>;
  items: Item[];
}

const fetchMenu = async (): Promise<{ categories: Category[] }> => {
  const res = await fetch('/api/menu');
  if (!res.ok) throw new Error('menu');
  return res.json();
};

export function MenuPage() {
  const { t, i18n } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ['menu'],
    queryFn: fetchMenu,
    onError: () => toast.error(t('error_menu')),
  });
  const add = useCartStore((s) => s.add);
  const lang = i18n.language;
  const items = data?.categories?.flatMap((c) => c.items) ?? [];

  return (
    <div>
      <Header />
      <h1>{t('menu')}</h1>
      {isPending ? (
        <MenuSkeleton />
      ) : isError ? (
        <EmptyState
          message={t('error_menu')}
          icon={<Utensils className="w-12 h-12 mx-auto" />}
        />
      ) : items.length === 0 ? (
        <EmptyState
          message={t('empty_menu')}
          icon={<Utensils className="w-12 h-12 mx-auto" />}
        />
      ) : (
        data?.categories?.map((cat) => (
          <div key={cat.id}>
            <h2>{cat.name_i18n[lang] || cat.name_i18n.en}</h2>
            {cat.items.map((item) => (
              <div key={item.id}>
                <span>{item.name_i18n[lang] || item.name_i18n.en}</span>
                <button
                  aria-label={`add ${item.name_i18n[lang] || item.name_i18n.en} to cart`}
                  onClick={() =>
                    add({ id: item.id, name: item.name_i18n.en, qty: 1 })
                  }
                >
                  +
                </button>
              </div>
            ))}
          </div>
        ))
      )}
    </div>
  );
}
