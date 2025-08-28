import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import baseConfig from '@neo/config/vite'

export default defineConfig({
  ...baseConfig,
  plugins: [react()],
})
