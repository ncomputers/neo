import type { Config } from 'tailwindcss';
import { colors } from './src/tokens';

export default {
  content: ['../**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors
    }
  },
  plugins: []
} satisfies Config;
