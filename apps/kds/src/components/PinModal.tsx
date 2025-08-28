import { useState } from 'react';
import { loginPin } from '@neo/api';

interface PinModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function PinModal({ open, onClose, onSuccess }: PinModalProps) {
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  if (!open) return null;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await loginPin({ phone, pin });
      localStorage.setItem('token', res.token);
      onSuccess();
      onClose();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
      <form onSubmit={submit} className="bg-white p-4 rounded space-y-2">
        <h2 className="text-lg font-semibold">Login</h2>
        {error && <div className="text-red-600">{error}</div>}
        <input
          className="border p-1 w-full"
          placeholder="Phone"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <input
          className="border p-1 w-full"
          placeholder="PIN"
          type="password"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
        />
        <div className="flex justify-end space-x-2 pt-2">
          <button type="button" onClick={onClose} className="px-2 py-1">Cancel</button>
          <button type="submit" className="px-2 py-1 bg-blue-600 text-white rounded">Login</button>
        </div>
      </form>
    </div>
  );
}
