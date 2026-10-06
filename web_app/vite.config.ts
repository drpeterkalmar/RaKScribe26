import { readFileSync } from 'node:fs'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

// Umbau Schritt 21 (Gutachten P2-12): Versionsnummer aus /VERSION in den Seitentitel (index.html: __RAKSCRIBE_VERSION__)
const VERSION = readFileSync(new URL('../VERSION', import.meta.url), 'utf8').trim()
const versionImTitel = (): Plugin => ({
  name: 'rakscribe-version',
  transformIndexHtml: (html) => html.replaceAll('__RAKSCRIBE_VERSION__', VERSION),
})

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), versionImTitel()],
  base: process.env.NODE_ENV === 'production' ? '/RaKScribe26/' : '/',
})
