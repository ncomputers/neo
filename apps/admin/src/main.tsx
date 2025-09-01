import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GlobalErrorBoundary, ThemeProvider, tokensFromOutlet, Toaster, toast } from '@neo/ui';
import { capturePageView } from '@neo/utils';
import './index.css';
import './i18n';
import { router } from './routes';
import { AuthProvider } from './auth';
import { withInterceptors } from '@neo/api';
import { refreshFlags } from '@neo/flags';

const qc = new QueryClient();

globalThis.fetch = withInterceptors(globalThis.fetch.bind(globalThis));
window.addEventListener('unauthorized', () => toast.error('Session expired'));

capturePageView(window.location.pathname);
router.subscribe((state) => {
  capturePageView(state.location.pathname);
});


async function init() {
  const [outlet] = await Promise.all([
    fetch('/api/outlet/theme').then(r => r.json()).catch(() => ({})),
    refreshFlags(),
  ]);
  const tokens = tokensFromOutlet(outlet);
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ThemeProvider theme={tokens}>
        <GlobalErrorBoundary>
          <QueryClientProvider client={qc}>
            <AuthProvider>
              <RouterProvider router={router} />
            </AuthProvider>
          </QueryClientProvider>
          <Toaster />
        </GlobalErrorBoundary>
      </ThemeProvider>
    </React.StrictMode>,
  );
}

init();
