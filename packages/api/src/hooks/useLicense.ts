import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { getLicenseStatus, LicenseStatus } from '../license';

export function useLicense(options?: UseQueryOptions<LicenseStatus>) {
  return useQuery<LicenseStatus>({
    queryKey: ['license'],
    queryFn: getLicenseStatus,
    ...options,
  });
}
