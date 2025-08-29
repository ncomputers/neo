import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { loginPin } from '@neo/api';

export function Login() {
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from?.pathname || '/kds/expo';
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        setError(null);
        try {
          await loginPin({ pin });
          navigate(from, { replace: true });
        } catch (err: any) {
          setError(err.message || 'Login failed');
        }
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
      {error && (
        <div role="alert" className="text-red-500">
          {error}
        </div>
      )}
    </form>
  );
}
