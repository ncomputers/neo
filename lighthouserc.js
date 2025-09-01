const guestUrl = process.env.GUEST_URL || 'http://localhost:5173';
const kdsUrl = process.env.KDS_URL || 'http://localhost:5174';
const adminUrl = process.env.ADMIN_URL || 'http://localhost:5175';

const useExternal = process.env.GUEST_URL && process.env.KDS_URL && process.env.ADMIN_URL;

module.exports = {
  ci: {
    collect: {
      url: [
        `${guestUrl}/menu`,
        `${kdsUrl}/kds/expo`,
        `${adminUrl}/dashboard`,
      ],
      startServerCommand: useExternal
        ? undefined
        : "(npx pnpm --filter @neo/guest preview --port 5173 --strictPort </dev/null & npx pnpm --filter @neo/kds preview --port 5174 --strictPort </dev/null & npx pnpm --filter @neo/admin preview --port 5175 --strictPort </dev/null & wait)",
      startServerReadyPattern: useExternal ? undefined : 'http://localhost:5175/',
      startServerReadyTimeout: 120000,
      numberOfRuns: 1,
      output: ['html'],
      reportFilenamePattern: '%%PATHNAME%%-lighthouse.%%EXTENSION%%',
      settings: {
        budgetsPath: 'budgets.json',
        chromeFlags: ['--no-sandbox'],
      },
    },
    assert: {
      assertMatrix: [
        {
          matchingUrlPattern: 'menu',
          assertions: {
            'categories:performance': ['error', { minScore: 0.9 }],
            'total-blocking-time': ['error', { maxNumericValue: 200, aggregationMethod: 'median' }],
            'largest-contentful-paint': ['error', { maxNumericValue: 2500, aggregationMethod: 'median' }],
            'installable-manifest': 'error',
          },
        },
        {
          matchingUrlPattern: 'kds/expo',
          assertions: {
            'categories:performance': ['error', { minScore: 0.85 }],
          },
        },
        {
          matchingUrlPattern: 'dashboard',
          assertions: {
            'categories:performance': ['error', { minScore: 0.85 }],
          },
        },
      ],
    },
  },
};
