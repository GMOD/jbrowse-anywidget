#!/bin/sh
# What the widget bundle must survive from a jbrowse-components change, run
# against the sibling checkout its `link:` dependencies resolve to
# (../jbrowse-components, already `pnpm install`ed). The test workflow runs it,
# nightly too, and jbrowse-components' downstream canary runs it against the
# commit under test, so a break shows up where it was made.
set -eu
cd "$(dirname "$0")/.."
pnpm install --frozen-lockfile=false
pnpm build

# No Node polyfills ship: it has no Buffer, and every `process` read sits
# behind a `typeof process` guard, so only NODE_ENV needs substituting. A
# dependency reaching for Buffer, or a vite config that drops the define,
# would otherwise surface only as a blank widget in a notebook.
fail=0
for f in jbrowse_anywidget/static/index.js jbrowse_anywidget/static/app.js; do
  # word boundary: ArrayBuffer.isView and any fooBuffer.bar are fine
  if grep -qE '(^|[^A-Za-z0-9_$])Buffer\.' "$f"; then
    echo "::error file=$f::Buffer is used but not polyfilled"
    fail=1
  fi
  if grep -q 'process\.env\.NODE_ENV' "$f"; then
    echo "::error file=$f::process.env.NODE_ENV was not substituted (vite define missing?)"
    fail=1
  fi
done
[ "$fail" = 0 ]

# esbuild does not typecheck, so a missing import builds and fails at runtime;
# tsc follows the linked packages into the checkout's TypeScript source.
pnpm typecheck
