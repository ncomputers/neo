import { createBrowserRouter, Navigate, RouteObject } from 'react-router-dom';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Floor } from './pages/Floor';
import { Billing } from './pages/Billing';
import { Referrals } from './pages/Referrals';
import { Onboarding } from './pages/Onboarding';
import { Support } from './pages/Support';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { SupportStaff } from './pages/SupportStaff';
import { Changelog } from './pages/Changelog';
import { Flags } from './pages/Flags';
import { Flag } from '@neo/ui';
import { QRPack } from './pages/QRPack';
import { Status } from './pages/Status';
import { Audit } from './pages/Audit';

export const routes: RouteObject[] = [
  { path: '/status', element: <Status /> },
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: (
      <ProtectedRoute roles={['owner', 'manager']}>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'floor', element: <Floor /> },

      { path: 'qr', element: <QRPack /> },
      {
        path: 'billing',
        element: (
          <ProtectedRoute roles={['owner']}>
            <Billing />
          </ProtectedRoute>
        )
      },
      {
        path: 'referrals',
        element: (
          <ProtectedRoute roles={['owner']}>
            <Referrals />
          </ProtectedRoute>
        )
      },
      { path: 'onboarding', element: <Onboarding /> },
      { path: 'audit', element: <Audit /> },
      { path: 'support', element: <Support /> },
      { path: 'changelog', element: <Flag name="changelog"><Changelog /></Flag> }
    ]

  },
  {
    path: '/staff',
    element: (
      <ProtectedRoute roles={['super_admin', 'support']}>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { path: 'support', element: <SupportStaff /> },
      { path: 'flags', element: <Flags /> },
    ],
  }
];

export const router = createBrowserRouter(routes);
