import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/sessions': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/zotero': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/metadata': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    target: 'es2020'
  },
  optimizeDeps: {
    exclude: ['pdfjs-dist']
  }
});
