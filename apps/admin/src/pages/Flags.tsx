import React, { useEffect, useState } from 'react';
import { refreshFlags } from '@neo/flags';
import { setFlag } from '@neo/api';
import { useAuth } from '../auth';

export function Flags() {
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const roles = useAuth();
  const canToggle = roles.includes('super_admin');

  useEffect(() => {
    refreshFlags().then(setFlags).catch(() => setFlags({}));
  }, []);

  async function toggle(name: string) {
    if (!canToggle) return;
    const next = !flags[name];
    setFlags({ ...flags, [name]: next });
    await setFlag(name, next);
    await refreshFlags().then(setFlags);
  }

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Feature Flags</h1>
      <ul>
        {Object.entries(flags).map(([name, value]) => (
          <li key={name} className="mb-2">
            {canToggle ? (
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={value} onChange={() => toggle(name)} />
                {name}
              </label>
            ) : (
              <span>
                {name}: {value ? 'on' : 'off'}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
