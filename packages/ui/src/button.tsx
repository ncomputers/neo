import { ButtonHTMLAttributes } from 'react';
import clsx from 'clsx';

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement>;

export function Button({ className, ...props }: ButtonProps) {
  return (
    <button
      className={clsx('px-3 py-1 rounded bg-primary text-white', className)}
      {...props}
    />
  );
}
