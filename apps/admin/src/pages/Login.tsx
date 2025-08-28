import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';

export function Login() {
  const [pin, setPin] = useState('');
  const login = useAuth((s) => s.login);
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from?.pathname || '/dashboard';
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        await login(pin);
        navigate(from, { replace: true });
      }}
      className="p-4 space-y-2"
    >
      <input
        value={pin}
        onChange={(e) => setPin(e.target.value)}
        placeholder="PIN"
        className="border p-2"
      />
      <button type="submit" className="block bg-blue-500 text-white p-2">
        Login
      </button>
    </form>
  );
}
