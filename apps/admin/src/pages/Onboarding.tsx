import { useState } from 'react';
import { ThemeProvider } from '@neo/ui';
import { Header } from '../components/Header';

export function Onboarding() {
  const [primary, setPrimary] = useState('#2563eb');
  const [logo, setLogo] = useState<string | undefined>();

  const onLogo = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setLogo(URL.createObjectURL(file));
    }
  };

  return (
    <div className="space-y-4 p-4">
      <div className="space-y-2">
        <label className="block">Primary Color</label>
        <input type="color" value={primary} onChange={(e) => setPrimary(e.target.value)} />
      </div>
      <div className="space-y-2">
        <label className="block">Logo</label>
        <input type="file" accept="image/*" onChange={onLogo} />
      </div>
      <div className="border p-4">
        <ThemeProvider theme={{ primary, accent: '#64748b', logoURL: logo }}>
          <Header />
          <button className="bg-primary text-white px-2 py-1">Preview Button</button>
        </ThemeProvider>
      </div>
    </div>
  );
}
