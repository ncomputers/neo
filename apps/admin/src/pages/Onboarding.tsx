import { useState } from 'react';

export function Onboarding() {
  const [color, setColor] = useState('#2563eb');
  const [logo, setLogo] = useState<string>('');

  const onColor = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setColor(value);
    document.documentElement.style.setProperty('--color-primary', value);
  };

  const onLogo = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setLogo(url);
    document.documentElement.style.setProperty('--logo-url', `url(${url})`);
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block mb-1">Primary Color</label>
        <input type="color" value={color} onChange={onColor} />
      </div>
      <div>
        <label className="block mb-1">Logo</label>
        <input type="file" accept="image/*" onChange={onLogo} />
      </div>
      <div
        className="h-24 w-48 border bg-no-repeat bg-contain"
        style={{ backgroundColor: 'var(--color-primary)', backgroundImage: 'var(--logo-url)' }}
      />
    </div>
  );
}
