import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster, GlobalErrorBoundary, ThemeProvider, tokensFromOutlet } from '@neo/ui';
import { capturePageView } from '@neo/utils';
import { initAnalytics, hasAnalyticsConsent } from './analytics';
import './index.css';
import './i18n';
import { AppRoutes } from './routes';
import { Workbox } from 'workbox-window';
import { retryQueuedOrders } from './queue';
import { handleSwMessage } from './sw-client';

const qc = new QueryClient();

if (hasAnalyticsConsent()) {
  initAnalytics();
  capturePageView(window.location.pathname);
}

if ('serviceWorker' in navigator) {
  const wb = new Workbox('/sw.js');
  navigator.serviceWorker.addEventListener('message', handleSwMessage);
  wb.register();
}

async function init() {
  const outlet = await fetch('/api/outlet/theme')
    .then(r => r.json())
    .catch(() => ({}));
  localStorage.setItem('outletInfo', JSON.stringify(outlet));
  const tokens = tokensFromOutlet(outlet);
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ThemeProvider theme={tokens}>
        <GlobalErrorBoundary>
          <QueryClientProvider client={qc}>
            <BrowserRouter>
              <AppRoutes />
            </BrowserRouter>
          </QueryClientProvider>
          <Toaster />
        </GlobalErrorBoundary>
      </ThemeProvider>
    </React.StrictMode>,
  );
}

init();

retryQueuedOrders((id) => (window.location.href = `/track/${id}`));
window.addEventListener('online', () => retryQueuedOrders((id) => (window.location.href = `/track/${id}`)));
