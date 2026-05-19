import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    base: '/',

    // ── Dev server ────────────────────────────────────────────────────────────
    server: {
      port: 5173,
      strictPort: false,
      // Proxy API calls to the FastAPI backend in dev so CORS is never an issue
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },

    // ── Production build ──────────────────────────────────────────────────────
    build: {
      outDir: 'dist',
      sourcemap: false,          // set to true if you want source maps in prod
      minify: 'oxc',
      chunkSizeWarningLimit: 800,
      rollupOptions: {
        output: {
          // Split vendor libs into a separate chunk for better caching
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
                return 'vendor';
              }
            }
          },
        },
      },
    },

    // ── Preview server (after `npm run build`) ────────────────────────────────
    preview: {
      port: 4173,
      strictPort: false,
    },
  }
})
