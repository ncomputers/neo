import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: { translation: { no_tickets: 'No tickets' } },
  es: { translation: { no_tickets: 'Sin tickets' } },
};

const lng = document.cookie.match(/(?:^|;)\s*glang=([^;]+)/)?.[1] || 'en';

i18n.use(initReactI18next).init({
  resources,
  lng,
  fallbackLng: 'en',
  interpolation: { escapeValue: false }
});

export default i18n;
