import { defineConfig } from 'vite';
import baseConfig from '@neo/config/vite';
import { resolve } from 'path';

export default defineConfig({
  ...baseConfig,
  build: {
    ...(baseConfig.build || {}),
    rollupOptions: {
      ...(baseConfig.build?.rollupOptions || {}),
      input: {
        main: resolve(__dirname, 'index.html'),
        sw: resolve(__dirname, 'src/sw.ts'),
      },
      output: {
        ...(baseConfig.build?.rollupOptions?.output || {}),
        entryFileNames: (chunk) =>
          chunk.name === 'sw' ? 'sw.js' : 'assets/[name]-[hash].js',
      },
    },
  },
});

