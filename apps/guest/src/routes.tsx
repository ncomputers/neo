import { Routes, Route, useLocation } from 'react-router-dom';
import { useEffect, useRef, lazy, Suspense } from 'react';
import { capturePageView } from '@neo/utils';

const Layout = lazy(() =>
  import('./components/Layout').then((m) => ({ default: m.Layout }))
);

const QrPage = lazy(() => import('./pages/QrPage').then(m => ({ default: m.QrPage })));
const MenuPage = lazy(() => import('./pages/MenuPage').then(m => ({ default: m.MenuPage })));
const CartPage = lazy(() => import('./pages/CartPage').then(m => ({ default: m.CartPage })));
const TrackPage = lazy(() => import('./pages/TrackPage').then(m => ({ default: m.TrackPage })));
const PayPage = lazy(() => import('./pages/Pay').then(m => ({ default: m.PayPage })));
const Health = lazy(() => import('./pages/Health').then(m => ({ default: m.Health })));
const Offline = lazy(() => import('./pages/Offline').then(m => ({ default: m.Offline })));

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
    <Suspense fallback={<div>Loading...</div>}>
      <Routes>
        <Route path="/health" element={<Health />} />
        <Route element={<Layout />}>
          <Route path="/" element={<QrPage />} />
          <Route path="/qr" element={<QrPage />} />
          <Route path="/menu" element={<MenuPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/track/:orderId" element={<TrackPage />} />
          <Route path="/pay/:orderId" element={<PayPage />} />
          <Route path="/offline" element={<Offline />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
