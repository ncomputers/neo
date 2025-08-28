import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { initCart } from '../store/cart';

export function QrPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const tenant = params.get('tenant') || '';
    const table = params.get('table') || '';
    initCart(tenant, table);
    localStorage.setItem('tenant', tenant);
    localStorage.setItem('table', table);
    navigate('/menu');
  }, [params, navigate]);

  return null;
}
