import type { Config } from 'tailwindcss';

export default {
  content: ['../**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: 'var(--color-primary)',
        secondary: 'var(--color-secondary)',
        success: 'var(--color-success)',
        warn: 'var(--color-warn)',
        error: 'var(--color-error)'
      }
    }
  },
  plugins: []
} satisfies Config;
