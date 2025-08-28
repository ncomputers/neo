import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster, GlobalErrorBoundary } from '@neo/ui';
import './index.css';
import './i18n';
import { AppRoutes } from './routes';
import { Workbox } from 'workbox-window';

const qc = new QueryClient();

if ('serviceWorker' in navigator) {
  const wb = new Workbox('/sw.js');
  wb.register();
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GlobalErrorBoundary>
      <QueryClientProvider client={qc}>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </QueryClientProvider>
      <Toaster />
    </GlobalErrorBoundary>
  </React.StrictMode>
);
