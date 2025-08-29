import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      menu: 'Menu',
      cart: 'Cart',
        place_order: 'Place order',
        license_expired: 'License expired',
        tip: 'Tip',
        empty_cart: 'Your cart is empty',
        empty_menu: 'No items available',
        error_menu: 'Failed to load menu',
        error_cart: 'Failed to load cart',
        error_order: 'Failed to place order',
        queued: 'Queued',
        poor_connection: 'Poor connection—some actions will be delayed',
        offline_notice: 'You’re offline. We’ll place your order when back online.',
        retry: 'Retry',
      },
  },
  es: {
    translation: {
      menu: 'Menú',
      cart: 'Carrito',
        place_order: 'Realizar pedido',
        license_expired: 'Licencia expirada',
        tip: 'Propina',
        empty_cart: 'Tu carrito está vacío',
        empty_menu: 'No hay artículos disponibles',
        error_menu: 'Error al cargar el menú',
        error_cart: 'Error al cargar el carrito',
        error_order: 'Error al realizar el pedido',
        queued: 'En cola',
        poor_connection: 'Conexión deficiente—algunas acciones se retrasarán',
        offline_notice: 'Estás sin conexión. Realizaremos tu pedido cuando vuelvas en línea.',
        retry: 'Reintentar',
      },
  },
};

const lng =
  document.cookie.match(/(?:^|;)\s*glang=([^;]+)/)?.[1] || 'en';

i18n.use(initReactI18next).init({
  resources,
  lng,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

export const setLanguage = (l: string) => {
  document.cookie = `glang=${l}`;
  i18n.changeLanguage(l);
};

export default i18n;
