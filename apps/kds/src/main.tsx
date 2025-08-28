import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster, GlobalErrorBoundary } from '@neo/ui';
import './index.css';
import './i18n';
import { Health } from './pages/Health';
import { Workbox } from 'workbox-window';
import { ExpoPage } from './pages/ExpoPage';

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
          <Routes>
            <Route path="/health" element={<Health />} />
            <Route path="/" element={<ExpoPage />} />
            <Route path="/kds/expo" element={<ExpoPage />} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
      <Toaster />
    </GlobalErrorBoundary>
  </React.StrictMode>
);
