import React, { useEffect, useState } from 'react';
import { loadFlags, setFlag } from '@neo/api';

export function Flags() {
  const [flags, setFlags] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadFlags().then(setFlags);
  }, []);

  async function toggle(name: string) {
    const next = !flags[name];
    setFlags({ ...flags, [name]: next });
    await setFlag(name, next);
  }

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Feature Flags</h1>
      <ul>
        {Object.entries(flags).map(([name, value]) => (
          <li key={name} className="mb-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={value}
                onChange={() => toggle(name)}
              />
              {name}
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

