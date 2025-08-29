import { apiFetch } from './api';

export interface LicenseStatus {
  status: 'ACTIVE' | 'GRACE' | 'EXPIRED';
  daysLeft?: number;
  renewUrl?: string;
}

export function getLicenseStatus() {
  return apiFetch<LicenseStatus>('/license');
}
