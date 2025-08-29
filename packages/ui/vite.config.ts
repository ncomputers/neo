import base from '@neo/config/vite'
import { defineConfig, mergeConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'

export default mergeConfig(
  base,
  defineConfig({
    resolve: {
      alias: {
        '@neo/api': fileURLToPath(new URL('../api/src/index.ts', import.meta.url)),
        '@neo/ui': fileURLToPath(new URL('./src/index.ts', import.meta.url)),
        '@neo/utils': fileURLToPath(new URL('../utils/src/index.ts', import.meta.url))
      }
    },
    test: {
      environment: 'jsdom'
    }
  })
)
