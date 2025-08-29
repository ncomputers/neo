import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect, useRef } from 'react';
import { capturePageView } from '@neo/utils';
import { Expo } from './pages/Expo';
import { Health } from './pages/Health';
import { Login } from './pages/Login';
import { ProtectedRoute } from './components/ProtectedRoute';

export function AppRoutes() {
  const loc = useLocation();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    capturePageView(loc.pathname);
  }, [loc.pathname]);
  return (
    <Routes>
      <Route path="/health" element={<Health />} />
      <Route path="/login" element={<Login />} />
        <Route path="/kds/expo" element={<ProtectedRoute roles={['kitchen', 'manager']}><Expo /></ProtectedRoute>} />
      <Route path="/" element={<Navigate to="/kds/expo" replace />} />
    </Routes>
  );
}
