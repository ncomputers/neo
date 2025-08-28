import { Routes, Route, Navigate } from 'react-router-dom';
import { Expo } from './pages/Expo';
import { Health } from './pages/Health';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/health" element={<Health />} />
      <Route path="/kds/expo" element={<Expo />} />
      <Route path="/" element={<Navigate to="/kds/expo" replace />} />
    </Routes>
  );
}
