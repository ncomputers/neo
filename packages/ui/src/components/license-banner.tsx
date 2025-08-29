export interface LicenseBannerProps {
  status?: 'ACTIVE' | 'GRACE' | 'EXPIRED';
  daysLeft?: number;
  renewUrl?: string;
}

export function LicenseBanner({ status, daysLeft, renewUrl }: LicenseBannerProps) {
  if (!status || status === 'ACTIVE') return null;
  const expired = status === 'EXPIRED';
  return (
    <div
      data-testid="license-banner"
      className={`${expired ? 'bg-red-600' : 'bg-yellow-500'} text-white p-2 text-center`}
    >
      {expired ? 'License expired' : `Subscription ends in ${daysLeft} days`}
      {renewUrl && (
        <a href={renewUrl} className="underline ml-2">
          Renew
        </a>
      )}
    </div>
  );
}
