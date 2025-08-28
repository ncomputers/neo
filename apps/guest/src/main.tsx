import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster, GlobalErrorBoundary } from '@neo/ui';
import './index.css';
import './i18n';
import { Health } from './pages/Health';
import { QrPage } from './pages/QrPage';
import { MenuPage } from './pages/MenuPage';
import { CartPage } from './pages/CartPage';
import { TrackPage } from './pages/TrackPage';
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
          <Routes>
            <Route path="/health" element={<Health />} />
            <Route path="/" element={<QrPage />} />
            <Route path="/qr" element={<QrPage />} />
            <Route path="/menu" element={<MenuPage />} />
            <Route path="/cart" element={<CartPage />} />
            <Route path="/track/:orderId" element={<TrackPage />} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
      <Toaster />
    </GlobalErrorBoundary>
  </React.StrictMode>
);
