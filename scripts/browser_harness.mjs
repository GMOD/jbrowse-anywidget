// What screenshot_examples.mjs and verify_bundle_runtime.mjs both need:
// @jbrowse/capture out of the sibling jbrowse-components checkout, a static server over this
// repo, and a browser that renders WebGL with no GPU. Shared because the two
// copies of it had already drifted — one launched a second identical browser for
// specs whose `headed` field was absent rather than false.

import { readFile } from 'node:fs/promises'
import { createServer } from 'node:http'
import { extname, join } from 'node:path'

// The sibling jbrowse-components checkout (override with
// PUPPETEER_FROM=/path/to/its/package.json), whose @jbrowse/capture source this
// imports directly: the readiness wait, and a launch that finds a system
// Chrome before puppeteer's own download.
const MONOREPO =
  process.env.PUPPETEER_FROM ??
  new URL('../../jbrowse-components/package.json', import.meta.url).pathname

const capture = await import(
  new URL('products/jbrowse-capture/src/index.ts', `file://${MONOREPO}`).href
)

export const { waitForJBrowseReady } = capture

/**
 * Browser-side source both harness pages start with: load a built bundle the
 * way anywidget delivers one. The kernel sends a `Path` _esm's file TEXT, and
 * the page blobs it, imports the blob, and revokes the URL — so the module a
 * notebook runs has an opaque `import.meta.url` and can resolve nothing
 * relative to itself. Importing it from its own http:// path instead is a
 * friendlier module than the real one, and the inlined RPC worker's whole
 * reason for existing would go untested. Interpolate into a page's module
 * script and call `loadAsAnywidgetDoes(path)`.
 */
export const ANYWIDGET_LOADER = `
async function loadAsAnywidgetDoes(path) {
  const esm = await (await fetch(path)).text()
  const url = URL.createObjectURL(new Blob([esm], { type: 'text/javascript' }))
  const mod = await import(url)
  URL.revokeObjectURL(url)
  return mod
}
`

export const REPO = new URL('..', import.meta.url).pathname

const TYPES = {
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.html': 'text/html',
  '.json': 'application/json',
}

/**
 * Serve this repo's files, with one generated page at /harness.html. Resolves to
 * the port and a close function. Port 0: the two scripts can run at once, and
 * neither collides with a dev server.
 */
export async function serveRepo(harness) {
  const server = createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost')
    if (url.pathname === '/harness.html') {
      res.setHeader('content-type', 'text/html')
      res.end(harness)
      return
    }
    try {
      const body = await readFile(join(REPO, url.pathname))
      // everything not listed is data (.gz, .tbi, .bw, ...), which the adapters
      // fetch by byte range and never sniff
      res.setHeader(
        'content-type',
        TYPES[extname(url.pathname)] ?? 'application/octet-stream',
      )
      res.end(body)
    } catch {
      res.statusCode = 404
      res.end('not found')
    }
  })
  await new Promise(r => {
    server.listen(0, r)
  })
  return {
    port: server.address().port,
    close: () => {
      server.close()
    },
  }
}

// Headless renders WebGL through swiftshader, which is enough for the genome
// views but paints nothing for molstar's 3D structure canvas. `headed` opens a
// real window on the host GPU instead — so those figures need a desktop session,
// and every other one keeps working over SSH/CI.
const SWIFTSHADER_ARGS = [
  '--enable-unsafe-swiftshader',
  '--use-gl=angle',
  '--use-angle=swiftshader',
  '--ignore-gpu-blocklist',
]

export function launch(headed = false) {
  return capture.launchBrowser({
    headless: !headed,
    args: headed ? [] : SWIFTSHADER_ARGS,
  })
}
