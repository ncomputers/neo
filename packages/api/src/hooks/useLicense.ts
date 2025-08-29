import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { getLicenseStatus, LicenseStatus } from '../endpoints';

export function useLicense(options?: UseQueryOptions<LicenseStatus>) {
  return useQuery<LicenseStatus>({
    queryKey: ['license'],
    queryFn: getLicenseStatus,
    ...options,
  });
}
