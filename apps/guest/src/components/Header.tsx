import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { setLanguage } from '../i18n';

export function Header() {
  const { i18n } = useTranslation();
  const [lang, setLang] = useState(i18n.language);

  const change = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const l = e.target.value;
    setLang(l);
    setLanguage(l);
  };

  return (
    <header className="p-2">
      <nav className="flex items-center justify-between" aria-label="Primary">
        <div
          className="h-8 w-24 bg-contain bg-no-repeat"
          style={{ backgroundImage: 'var(--logo-url)' }}
        />
        <select aria-label="language" value={lang} onChange={change}>
          <option value="en">EN</option>
          <option value="es">ES</option>
        </select>
      </nav>
    </header>
  );
}
