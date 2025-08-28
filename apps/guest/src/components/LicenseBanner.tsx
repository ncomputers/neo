import { useTranslation } from 'react-i18next';
import { useLicense } from '../hooks/useLicense';

export function LicenseBanner() {
  const { t } = useTranslation();
  const { data } = useLicense();

  if (data?.status === 'GRACE') {
    return (
      <div data-testid="license-banner">
        {t('license_grace')}{' '}
        <a href="/admin/billing">{t('renew')}</a>
      </div>
    );
  }

  if (data?.status === 'EXPIRED') {
    return (
      <div data-testid="license-banner">
        {t('license_expired')}{' '}
        <a href="/admin/billing">{t('renew')}</a>
      </div>
    );
  }

  return null;
}

