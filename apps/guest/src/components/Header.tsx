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
    <header className="p-2 flex justify-end">
      <select aria-label="language" value={lang} onChange={change}>
        <option value="en">EN</option>
        <option value="es">ES</option>
      </select>
    </header>
  );
}
