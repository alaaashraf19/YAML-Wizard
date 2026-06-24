import { defineConfig, loadEnv } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Explicitly load .env from current directory
  const env = loadEnv(mode, process.cwd(), '')
  
  console.log('🔍 Mode:', mode)
  console.log('🔍 VITE_API_URL from .env:', env.VITE_API_URL)
  console.log('🔍 VITE_API_URL from process.env:', process.env.VITE_API_URL)
  
  return {
    plugins: [
      react(),
      babel({ presets: [reactCompilerPreset()] })
    ],
  }
})