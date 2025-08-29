import React, { PropsWithChildren } from 'react';
import { useFlag } from '@neo/flags';

interface FlagProps extends PropsWithChildren {
  name: string;
  fallback?: React.ReactNode;
}

export function Flag({ name, children, fallback = null }: FlagProps) {
  return useFlag(name) ? <>{children}</> : <>{fallback}</>;
}
