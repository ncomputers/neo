import { useQuery } from '@tanstack/react-query';

export function useLicense() {
  return useQuery<{ status: string }>({
    queryKey: ['license'],
    queryFn: async () => {
      const res = await fetch('/api/license');
      if (!res.ok) throw new Error('license');
      return res.json();
    },
  });
}
