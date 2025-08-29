import { createBrowserRouter, Navigate, RouteObject } from 'react-router-dom';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Floor } from './pages/Floor';
import { Billing } from './pages/Billing';
import { Onboarding } from './pages/Onboarding';
import { Support } from './pages/Support';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { StaffSupport } from './pages/StaffSupport';

export const routes: RouteObject[] = [
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
        {
          path: 'billing',
          element: (
            <ProtectedRoute roles={['owner']}>
              <Billing />
            </ProtectedRoute>
          )
        },
        { path: 'onboarding', element: <Onboarding /> },
        { path: 'support', element: <Support /> }
      ]
    }
  },
  {
    path: '/staff',
    element: (
      <ProtectedRoute roles={['super_admin', 'support']}>
        <Layout />
      </ProtectedRoute>
    ),
    children: [{ path: 'support', element: <StaffSupport /> }],
  }
];

export const router = createBrowserRouter(routes);
