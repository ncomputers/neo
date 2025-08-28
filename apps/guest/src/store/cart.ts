import { create } from 'zustand';

export interface CartItem {
  id: string;
  name: string;
  qty: number;
}

let key = 'cart';

interface CartState {
  items: CartItem[];
  add: (item: CartItem) => void;
  clear: () => void;
}

export const initCart = (tenant: string, table: string) => {
  key = `cart:${tenant}:${table}`;
  const stored = localStorage.getItem(key);
  if (stored) useCartStore.setState({ items: JSON.parse(stored) });
};

export const useCartStore = create<CartState>((set, get) => ({
  items: [],
  add: (item) => {
    const existing = get().items.find((i) => i.id === item.id);
    let items;
    if (existing) {
      items = get().items.map((i) =>
        i.id === item.id ? { ...i, qty: i.qty + item.qty } : i
      );
    } else {
      items = [...get().items, item];
    }
    localStorage.setItem(key, JSON.stringify(items));
    set({ items });
  },
  clear: () => {
    localStorage.removeItem(key);
    set({ items: [] });
  },
}));
