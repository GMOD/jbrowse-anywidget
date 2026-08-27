// What screenshot_examples.mjs and verify_bundle_runtime.mjs both need: puppeteer
// out of the sibling jbrowse-components checkout, a static server over this
// repo, and a browser that renders WebGL with no GPU. Shared because the two
// copies of it had already drifted — one launched a second identical browser for
// specs whose `headed` field was absent rather than false.

import { readFile } from 'node:fs/promises'
import { createServer } from 'node:http'
import { createRequire } from 'node:module'
import { extname, join } from 'node:path'

// puppeteer isn't a dep of this repo; resolve it from the sibling
// jbrowse-components checkout (override with PUPPETEER_FROM=/path/to/pkg-dir).
export const MONOREPO =
  process.env.PUPPETEER_FROM ??
  new URL('../../jbrowse-components/package.json', import.meta.url).pathname

export const puppeteer = createRequire(MONOREPO)('puppeteer')

/** Resolve a path inside that checkout, for importing its source directly. */
export const fromMonorepo = subpath =>
  new URL(subpath, `file://${MONOREPO}`).href

// The chrome-picking half of the same borrowing: CHROME_PATH, then the first
// installed system browser, then puppeteer's own download. Without it a box
// that has google-chrome but has never run `puppeteer browsers install` fails
// at launch with a version string and no hint.
const { findChromeExecutable } = await import(
  fromMonorepo('products/jbrowse-capture/src/browser.ts')
)

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
const HEADLESS_ARGS = [
  '--no-sandbox',
  '--enable-unsafe-swiftshader',
  '--use-gl=angle',
  '--use-angle=swiftshader',
  '--ignore-gpu-blocklist',
]

export function launch(headed = false) {
  return puppeteer.launch({
    headless: !headed,
    executablePath: findChromeExecutable(),
    args: headed ? ['--no-sandbox'] : HEADLESS_ARGS,
  })
}
