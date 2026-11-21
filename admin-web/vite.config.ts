import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const spaOutDir = path.resolve(__dirname, '../backend/app/static/admin-spa')

function preserveGitkeep(): Plugin {
  return {
    name: 'preserve-gitkeep',
    closeBundle() {
      fs.mkdirSync(spaOutDir, { recursive: true })
      const gitkeep = path.join(spaOutDir, '.gitkeep')
      if (!fs.existsSync(gitkeep)) {
        fs.writeFileSync(gitkeep, '')
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), preserveGitkeep()],
  base: '/admin/ui/',
  build: {
    outDir: spaOutDir,
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8765',
      '/health': 'http://127.0.0.1:8765',
      '/admin/ui/login': 'http://127.0.0.1:8765',
      '/admin/ui/api': 'http://127.0.0.1:8765',
      '/admin/ui/logout': 'http://127.0.0.1:8765',
      '/admin/ui/lang': 'http://127.0.0.1:8765',
    },
  },
})