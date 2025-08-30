import React, { useEffect, useState } from 'react';
import { refreshFlags } from '@neo/flags';
import { useAuth } from '../auth';

export function Flags() {
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const roles = useAuth();
  const isAdmin = roles.includes('super_admin');

  useEffect(() => {
    refreshFlags().then(setFlags).catch(() => setFlags({}));
  }, []);

  async function toggle(name: string) {
    const next = !flags[name];
    setFlags({ ...flags, [name]: next });
    await fetch(`/admin/flags/${name}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ value: next }),
    });
    setFlags(await refreshFlags());
  }

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Feature Flags</h1>
      <ul>
        {Object.entries(flags).map(([name, value]) => (
          <li key={name} className="mb-2">
            {isAdmin ? (
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={value}
                  onChange={() => toggle(name)}
                />
                {name}
              </label>
            ) : (
              <span>
                {name}: {String(value)}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

