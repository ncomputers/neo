import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { capturePageView } from '@neo/utils';
import { Expo } from './pages/Expo';
import { Health } from './pages/Health';
import { Login } from './pages/Login';
import { Protected } from './components/Protected';

export function AppRoutes() {
  const loc = useLocation();
  useEffect(() => {
    capturePageView(loc.pathname);
  }, [loc.pathname]);
  return (
    <Routes>
      <Route path="/health" element={<Health />} />
      <Route path="/login" element={<Login />} />
      <Route path="/kds/expo" element={<Protected><Expo /></Protected>} />
      <Route path="/" element={<Navigate to="/kds/expo" replace />} />
    </Routes>
  );
}
