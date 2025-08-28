import { ReactNode } from 'react';
import clsx from 'clsx';

export interface EmptyStateProps {
  message: string;
  icon?: ReactNode;
  className?: string;
}

export function EmptyState({ message, icon, className }: EmptyStateProps) {
  return (
    <div className={clsx('p-4 text-center text-gray-500 space-y-2', className)}>
      {icon && <div className="mx-auto w-16 h-16 text-gray-400">{icon}</div>}
      <p>{message}</p>
    </div>
  );
}

export default EmptyState;
