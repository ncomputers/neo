import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { capturePageView } from '@neo/utils';
import { Expo } from './pages/Expo';
import { Health } from './pages/Health';
import { Layout } from './components/Layout';

export function AppRoutes() {
  const loc = useLocation();
  useEffect(() => {
    capturePageView(loc.pathname);
  }, [loc.pathname]);
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/health" element={<Health />} />
        <Route path="/kds/expo" element={<Expo />} />
        <Route path="/" element={<Navigate to="/kds/expo" replace />} />
      </Route>
    </Routes>
  );
}
