import { useEffect, useState } from 'react';
import { enableAnalytics, disableAnalytics } from '../analytics';
import { capturePageView } from '@neo/utils';

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (localStorage.getItem('analytics-consent') === null) {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  const accept = () => {
    enableAnalytics();
    capturePageView(window.location.pathname);
    setVisible(false);
  };

  const decline = () => {
    disableAnalytics();
    setVisible(false);
  };

  return (
    <div className="fixed bottom-0 inset-x-0 p-4 bg-gray-900 text-white text-sm">
      <p className="mb-2">
        We use cookies for analytics. Read our{' '}
        <a href="/privacy" className="underline">
          Privacy Policy
        </a>
        .
      </p>
      <div className="flex gap-2">
        <button onClick={accept} className="bg-white text-black px-2 py-1 rounded">
          Accept
        </button>
        <button onClick={decline} className="bg-gray-700 px-2 py-1 rounded">
          Decline
        </button>
      </div>
    </div>
  );
}
