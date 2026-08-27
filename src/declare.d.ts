// side-effect imports of assets the bundler handles but tsc has no types for
declare module '@fontsource/roboto'
declare module '@jbrowse/react-app2/styles.css'

// Vite's inlined-worker import. The `?worker` spelling is the exception the
// embedded products' own `makeWorkerInstance` avoids — `new Worker(new
// URL('./rpcWorker', import.meta.url))` is the portable form — but that form
// throws here: anywidget imports this bundle from a blob URL, and a blob URL is
// opaque, so it cannot be a base for a relative one. Inlining is the only
// spelling that needs no second file, and `?worker&inline` is how Vite writes
// it. See vite.config.js.
declare module '*?worker&inline' {
  const WorkerFactory: new () => Worker
  export default WorkerFactory
}
