import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from '@neo/ui';
import { setLanguage } from '../i18n';

export function Header() {
  const { i18n } = useTranslation();
  const [lang, setLang] = useState(i18n.language);
  const { logoURL } = useTheme();

  const change = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const l = e.target.value;
    setLang(l);
    setLanguage(l);
  };

  return (
    <header className="p-2 flex justify-between items-center">
      {logoURL && <img src={logoURL} alt="logo" className="h-6" />}
      <select aria-label="language" value={lang} onChange={change}>
        <option value="en">EN</option>
        <option value="es">ES</option>
      </select>
    </header>
  );
}
