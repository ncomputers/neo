import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GlobalErrorBoundary, ThemeProvider, tokensFromOutlet } from '@neo/ui';
import { capturePageView } from '@neo/utils';
import './index.css';
import './i18n';
import { router } from './routes';
import { Workbox } from 'workbox-window';

const qc = new QueryClient();

capturePageView(window.location.pathname);
router.subscribe((state) => {
  capturePageView(state.location.pathname);
});

if ('serviceWorker' in navigator) {
  const wb = new Workbox('/sw.js');
  wb.register();
}

async function init() {
  const outlet = await fetch('/api/outlet/theme').then(r => r.json()).catch(() => ({}));
  const tokens = tokensFromOutlet(outlet);
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ThemeProvider theme={tokens}>
        <GlobalErrorBoundary>
          <QueryClientProvider client={qc}>
            <RouterProvider router={router} />
          </QueryClientProvider>
        </GlobalErrorBoundary>
      </ThemeProvider>
    </React.StrictMode>,
  );
}

init();
