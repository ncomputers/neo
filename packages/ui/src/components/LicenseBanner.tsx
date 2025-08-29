import clsx from 'clsx';

export interface LicenseBannerProps {
  status: 'ACTIVE' | 'GRACE' | 'EXPIRED';
  daysLeft?: number;
  renewUrl?: string;
}

export function LicenseBanner({ status, daysLeft, renewUrl }: LicenseBannerProps) {
  if (status === 'ACTIVE') return null;
  const expired = status === 'EXPIRED';
  return (
    <div
      className={clsx(
        'p-2 text-center text-sm',
        expired ? 'bg-red-600 text-white' : 'bg-blue-100 text-blue-800'
      )}
    >
      {expired ? 'License expired' : `Subscription ends in ${daysLeft ?? 0} days`}
      {renewUrl && (
        <>
          {' '}
          <a href={renewUrl} className="underline">
            Renew
          </a>
        </>
      )}
    </div>
  );
}
