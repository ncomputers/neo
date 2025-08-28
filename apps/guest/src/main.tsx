import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { Toaster, GlobalErrorBoundary, ThemeProvider, tokensFromOutlet } from '@neo/ui';
import './index.css';
import './i18n';
import { AppRoutes } from './routes';
import { Workbox } from 'workbox-window';
import { API_BASE } from './env';

const qc = new QueryClient();

if ('serviceWorker' in navigator) {
  const wb = new Workbox('/sw.js');
  wb.register();
}

function App() {
  const { data: outlet } = useQuery({
    queryKey: ['outlet'],
    queryFn: () => fetch(`${API_BASE}/outlet`).then((r) => r.json())
  });
  return (
    <ThemeProvider theme={tokensFromOutlet(outlet)}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ThemeProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GlobalErrorBoundary>
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>
      <Toaster />
    </GlobalErrorBoundary>
  </React.StrictMode>,
);
