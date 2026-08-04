import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Two independent single-file ESM bundles, each loaded by an anywidget via
// _esm: the default `index.js` (lean linear-genome-view) and, when JB_TARGET=app,
// `app.js` (the full multi-view app for synteny/dotplot/etc). They are built by
// separate `vite build` invocations (see package.json) because inlineDynamicImports
// — which keeps each to one runtime-resolvable file — forbids multiple entries in
// one build. RPC runs on the main thread (no makeWorkerInstance) in both.
const isApp = process.env.JB_TARGET === 'app'

export default defineConfig({
  plugins: [react()],
  // No Node polyfills: the bundle has no Buffer at all, and every `process`
  // read but this one sits behind a `typeof process` guard. Only NODE_ENV needs
  // substituting — vite's lib mode leaves it alone, which would leave React and
  // MobX reading a `process` that isn't there. vite-plugin-node-polyfills used
  // to stand in for all of this, along with a shim for the `stream/web` its own
  // `stream` alias broke, and cost ~1.3MB of shims for one identifier. CI
  // asserts the bundle stays free of unpolyfilled globals.
  define: { 'process.env.NODE_ENV': '"production"' },
  resolve: {
    // The linked @jbrowse/react-linear-genome-view2 resolves react/mobx from
    // the monorepo's node_modules — a second copy. Dedupe the packages present
    // in both trees to one instance, or hooks/MobX break ("invalid hook call",
    // multiple mobx instances). This repo's versions must therefore track the
    // monorepo's: dedupe makes the version here win.
    dedupe: ['react', 'react-dom', 'react/jsx-runtime', 'mobx'],
  },
  build: {
    outDir: 'jbrowse_anywidget/static',
    // only the first (lgv) build clears the dir; the app build appends to it
    emptyOutDir: !isApp,
    lib: {
      entry: isApp ? 'src/app.ts' : 'src/index.ts',
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
