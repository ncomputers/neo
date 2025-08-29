import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { getLicenseStatus, LicenseStatus } from '../endpoints';

export function useLicenseStatus(options?: UseQueryOptions<LicenseStatus>) {
  return useQuery<LicenseStatus>({
    queryKey: ['license'],
    queryFn: getLicenseStatus,
    ...options,
  });
}
