import base from '@neo/config/vite';
import { defineConfig, mergeConfig } from 'vite';
import { fileURLToPath, URL } from 'node:url';

export default mergeConfig(
  base,
  defineConfig({
    resolve: {
      alias: {
        '@neo/api': fileURLToPath(new URL('../../packages/api/src/index.ts', import.meta.url)),
        '@neo/ui': fileURLToPath(new URL('../../packages/ui/src/index.ts', import.meta.url)),
        '@neo/utils': fileURLToPath(new URL('../../packages/utils/src/index.ts', import.meta.url)),
        '@neo/flags': fileURLToPath(new URL('../../packages/flags/src/index.ts', import.meta.url))
      }
    },
    test: {
      environment: 'jsdom',
      setupFiles: './vitest.setup.ts'
    }
  })
);
