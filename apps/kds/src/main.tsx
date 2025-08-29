import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster, GlobalErrorBoundary, ThemeProvider, tokensFromOutlet, toast } from '@neo/ui';
import './index.css';
import './i18n';
import { Workbox } from 'workbox-window';
import { AppRoutes } from './routes';
import { AuthProvider } from './auth';
import { addFetchInterceptors } from '@neo/api';

const qc = new QueryClient();

const fetcher = addFetchInterceptors(window.fetch.bind(window));
(window as any).fetch = fetcher;
window.addEventListener('unauthorized', () => toast.error('Session expired'));

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
            <AuthProvider>
              <BrowserRouter>
                <AppRoutes />
              </BrowserRouter>
            </AuthProvider>
          </QueryClientProvider>
          <Toaster />
        </GlobalErrorBoundary>
      </ThemeProvider>
    </React.StrictMode>,
  );
}

init();
