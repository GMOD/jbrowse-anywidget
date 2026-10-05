# The readiness waits live in @jbrowse/capture now

`scripts/screenshot_examples.mjs` imports them from
`products/jbrowse-capture/src/index.ts`, not the
`packages/browser-test-utils/src/waits.ts` they used to be at — that path no
longer exists and the nightly `render` job died at the import with
`ERR_MODULE_NOT_FOUND`. `scripts/browser_harness.mjs` borrows
`findChromeExecutable` from the same package, so a box with a system Chrome and
no `puppeteer browsers install` runs the harness anyway.

`browser_harness.mjs` is where both `.mjs` scripts get puppeteer, the static
server and the swiftshader launch flags. They had two copies and the copies had
drifted: the screenshot one keyed its browser cache on the raw `headed` field,
so a spec that omitted it and a spec that set it `false` were two entries and
two Chromes.
