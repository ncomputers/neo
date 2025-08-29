import React, { PropsWithChildren } from 'react';
import { getFlag } from '@neo/api';

interface FeatureFlagProps extends PropsWithChildren {
  name: string;
  fallback?: React.ReactNode;
}

export function FeatureFlag({ name, children, fallback = null }: FeatureFlagProps) {
  return getFlag(name) ? <>{children}</> : <>{fallback}</>;
}

