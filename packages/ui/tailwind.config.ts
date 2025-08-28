import type { Config } from 'tailwindcss';

export default {
  content: ['../**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#2563eb',
        secondary: '#64748b',
        success: '#16a34a',
        warn: '#f59e0b',
        error: '#dc2626'
      }
    }
  },
  plugins: []
} satisfies Config;
