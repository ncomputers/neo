import { Routes, Route, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { capturePageView } from '@neo/utils';
import { QrPage } from './pages/QrPage';
import { MenuPage } from './pages/MenuPage';
import { CartPage } from './pages/CartPage';
import { TrackPage } from './pages/TrackPage';
import { PayPage } from './pages/Pay';
import { Health } from './pages/Health';
import { Layout } from './components/Layout';

export function AppRoutes() {
  const loc = useLocation();
  useEffect(() => {
    capturePageView(loc.pathname);
  }, [loc.pathname]);
  return (
    <Routes>
      <Route path="/health" element={<Health />} />
      <Route element={<Layout />}>
        <Route path="/" element={<QrPage />} />
        <Route path="/qr" element={<QrPage />} />
        <Route path="/menu" element={<MenuPage />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/track/:orderId" element={<TrackPage />} />
        <Route path="/pay/:orderId" element={<PayPage />} />
      </Route>
    </Routes>
  );
}
