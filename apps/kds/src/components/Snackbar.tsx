import { useEffect } from 'react';

export interface SnackbarProps {
  message: string;
  type?: 'success' | 'error';
  onClose: () => void;
}

export function Snackbar({ message, type = 'success', onClose }: SnackbarProps) {
  useEffect(() => {
    const t = setTimeout(onClose, 3000);
    return () => clearTimeout(t);
  }, [onClose]);
  const color = type === 'error' ? 'bg-red-600' : 'bg-green-600';
  return (
    <div className={`fixed bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded text-white ${color}`}>{message}</div>
  );
}
