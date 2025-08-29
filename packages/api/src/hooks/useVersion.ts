import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { getVersion, VersionInfo } from '../version';

export function useVersion(options?: UseQueryOptions<VersionInfo>) {
  return useQuery<VersionInfo>({
    queryKey: ['version'],
    queryFn: getVersion,
    ...options,
  });
}
