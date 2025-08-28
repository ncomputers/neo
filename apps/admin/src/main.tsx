import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { ThemeProvider, tokensFromOutlet } from '@neo/ui';
import './index.css';
import './i18n';
import { Health } from './pages/Health';
import { Onboarding } from './pages/Onboarding';
import { Header } from './components/Header';
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
        <Header />
        <Routes>
          <Route path="/health" element={<Health />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/" element={<Health />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
