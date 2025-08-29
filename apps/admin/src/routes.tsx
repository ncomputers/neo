import { createBrowserRouter, Navigate, RouteObject } from 'react-router-dom';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Floor } from './pages/Floor';
import { Billing } from './pages/Billing';
import { Onboarding } from './pages/Onboarding';
import { Layout } from './components/Layout';
import { Protected } from './components/Protected';

export const routes: RouteObject[] = [
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: (
      <Protected>
        <Layout />
      </Protected>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'floor', element: <Floor /> },
      {
        path: 'billing',
        element: (
          <Protected roles={['owner']}>
            <Billing />
          </Protected>
        )
      },
      { path: 'onboarding', element: <Onboarding /> }
    ]
  }
];

export const router = createBrowserRouter(routes);
