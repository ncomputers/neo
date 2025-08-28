import { Routes, Route } from 'react-router-dom';
import { QrPage } from './pages/QrPage';
import { MenuPage } from './pages/MenuPage';
import { CartPage } from './pages/CartPage';
import { TrackPage } from './pages/TrackPage';
import { PayPage } from './pages/Pay';
import { Health } from './pages/Health';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/health" element={<Health />} />
      <Route path="/" element={<QrPage />} />
      <Route path="/qr" element={<QrPage />} />
      <Route path="/menu" element={<MenuPage />} />
      <Route path="/cart" element={<CartPage />} />
      <Route path="/track/:orderId" element={<TrackPage />} />
      <Route path="/pay/:orderId" element={<PayPage />} />
    </Routes>
  );
}
