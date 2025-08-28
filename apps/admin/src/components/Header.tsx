import { useTheme } from '@neo/ui';

export function Header() {
  const { logoURL } = useTheme();
  return (
    <header className="p-2">
      {logoURL && <img src={logoURL} alt="logo" className="h-6" />}
    </header>
  );
}
