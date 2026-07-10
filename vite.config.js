import { createRequire } from 'node:module'
import { dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

const require = createRequire(import.meta.url)

const streamWebShim = fileURLToPath(
  new URL('./src/stream-web-shim.js', import.meta.url),
)

// vite-plugin-node-polyfills injects `import 'vite-plugin-node-polyfills/shims/<x>'`
// into any module that references process/global/Buffer. Modules pulled in
// through the linked (monorepo) @jbrowse packages live outside this repo's
// node_modules, so that bare specifier can't resolve from their location. Pin
// the three shims to this repo's copy by resolving them here.
const shimAliases = ['process', 'global', 'buffer'].map(name => ({
  find: `vite-plugin-node-polyfills/shims/${name}`,
  replacement: dirname(
    dirname(require.resolve(`vite-plugin-node-polyfills/shims/${name}`)),
  ),
}))

// Two independent single-file ESM bundles, each loaded by an anywidget via
// _esm: the default `index.js` (lean linear-genome-view) and, when JB_TARGET=app,
// `app.js` (the full multi-view app for synteny/dotplot/etc). They are built by
// separate `vite build` invocations (see package.json) because inlineDynamicImports
// — which keeps each to one runtime-resolvable file — forbids multiple entries in
// one build. RPC runs on the main thread (no makeWorkerInstance) in both.
const isApp = process.env.JB_TARGET === 'app'

export default defineConfig({
  plugins: [
    // nodePolyfills adds a `stream` prefix-alias that rewrites `stream/web` to
    // the nonexistent `stream-browserify/web`. Vite's alias plugin runs before
    // any resolveId hook, so intercepting isn't enough — this pre-enforced
    // plugin catches `stream/web` wherever it lands and points at the browser's
    // native WHATWG streams.
    {
      name: 'stream-web-shim',
      enforce: 'pre',
      resolveId(id) {
        const web =
          id === 'stream/web' ||
          id === 'node:stream/web' ||
          id.endsWith('stream-browserify/web')
        return web ? streamWebShim : null
      },
    },
    react(),
    nodePolyfills({ exclude: ['stream/web'] }),
  ],
  resolve: {
    // The linked @jbrowse/react-linear-genome-view2 resolves react/mobx from
    // the monorepo's node_modules — a second copy. Dedupe the packages present
    // in both trees to one instance, or hooks/MobX break ("invalid hook call",
    // multiple mobx instances).
    dedupe: ['react', 'react-dom', 'react/jsx-runtime', 'mobx'],
    alias: shimAliases,
  },
  build: {
    outDir: 'jbrowse_anywidget/static',
    // only the first (lgv) build clears the dir; the app build appends to it
    emptyOutDir: !isApp,
    lib: {
      entry: isApp ? 'src/app.jsx' : 'src/index.jsx',
      formats: ['es'],
      fileName: () => (isApp ? 'app.js' : 'index.js'),
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
})
