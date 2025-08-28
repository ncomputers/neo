import { Routes, Route } from 'react-router-dom';
import { QrPage } from './pages/QrPage';
import { MenuPage } from './pages/MenuPage';
import { CartPage } from './pages/CartPage';
import { TrackPage } from './pages/TrackPage';
import { Health } from './pages/Health';
import { useLicense } from './hooks/useLicense';

export function AppRoutes() {
  useLicense();
  return (
    <Routes>
      <Route path="/health" element={<Health />} />
      <Route path="/" element={<QrPage />} />
      <Route path="/qr" element={<QrPage />} />
      <Route path="/menu" element={<MenuPage />} />
      <Route path="/cart" element={<CartPage />} />
      <Route path="/track/:orderId" element={<TrackPage />} />
    </Routes>
  );
}
