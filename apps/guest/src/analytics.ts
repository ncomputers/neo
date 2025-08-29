import posthog from 'posthog-js';

const CONSENT_KEY = 'consent';
let initialized = false;

export function hasAnalyticsConsent() {
  return localStorage.getItem(CONSENT_KEY) === 'accepted';
}

export function initAnalytics() {
  if (initialized || !hasAnalyticsConsent()) return;
  const key = import.meta.env.VITE_POSTHOG_KEY;
  if (!key) return;
  posthog.init(key, { api_host: import.meta.env.VITE_POSTHOG_HOST });
  initialized = true;
}

export function enableAnalytics() {
  localStorage.setItem(CONSENT_KEY, 'accepted');
  initAnalytics();
  posthog.opt_in_capturing();
}

export function disableAnalytics() {
  localStorage.setItem(CONSENT_KEY, 'declined');
  posthog.opt_out_capturing();
}
