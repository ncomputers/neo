import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Header } from '../components/Header';
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
  const { data } = useQuery({ queryKey: ['menu'], queryFn: fetchMenu });
  const add = useCartStore((s) => s.add);
  const lang = i18n.language;

  return (
    <div>
      <Header />
      <h1>{t('menu')}</h1>
      {data?.categories?.map((cat) => (
        <div key={cat.id}>
          <h2>{cat.name_i18n[lang] || cat.name_i18n.en}</h2>
          {cat.items.map((item) => (
            <div key={item.id}>
              <span>{item.name_i18n[lang] || item.name_i18n.en}</span>
              <button
                onClick={() =>
                  add({ id: item.id, name: item.name_i18n.en, qty: 1 })
                }
              >
                +
              </button>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
