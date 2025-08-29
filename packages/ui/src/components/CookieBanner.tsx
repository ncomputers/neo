import { useEffect, useState } from 'react';

export interface CookieBannerProps {
  onAccept?: () => void;
  onDecline?: () => void;
}

const CONSENT_KEY = 'consent';

export function CookieBanner({ onAccept, onDecline }: CookieBannerProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(CONSENT_KEY) === null) {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  const accept = () => {
    localStorage.setItem(CONSENT_KEY, 'accepted');
    onAccept?.();
    setVisible(false);
  };

  const decline = () => {
    localStorage.setItem(CONSENT_KEY, 'declined');
    onDecline?.();
    setVisible(false);
  };

  return (
    <div className="fixed bottom-0 inset-x-0 p-4 bg-gray-900 text-white text-sm">
      <p className="mb-2">We use cookies for analytics only.</p>
      <div className="flex gap-2">
        <button onClick={accept} className="bg-white text-black px-2 py-1 rounded">Accept</button>
        <button onClick={decline} className="bg-gray-700 px-2 py-1 rounded">Decline</button>
      </div>
    </div>
  );
}
