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
    },
  },
  es: {
    translation: {
      menu: 'Menú',
      cart: 'Carrito',
      place_order: 'Realizar pedido',
      license_expired: 'Licencia expirada',
      tip: 'Propina',
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
