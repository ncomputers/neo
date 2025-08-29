import React, { PropsWithChildren } from 'react';
import { getFlag } from '@neo/api';

interface FlagProps extends PropsWithChildren {
  name: string;
  fallback?: React.ReactNode;
}

export function Flag({ name, children, fallback = null }: FlagProps) {
  return getFlag(name) ? <>{children}</> : <>{fallback}</>;
}

