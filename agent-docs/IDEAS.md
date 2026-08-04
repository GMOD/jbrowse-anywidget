# Ideas

Deferred work worth revisiting. Not a roadmap — things we decided not to do yet,
with enough context to pick up cold.

## JBrowseApp is write-once from Python

`LinearGenomeView` has a real two-way loop: `location` syncs both directions, so
a slider or a computation can drive the view and a pan can drive Python.
`JBrowseApp` has only half of it. `view_locations` is read-back only, and every
config trait (`assemblies`, `tracks`, `views`, `plugins`) tears down and
rebuilds the whole app on change — see the `rebuild` handler in `src/app.ts`. So
there is no way to pan a synteny or dotplot view from Python short of recreating
it, and a rebuild loses all view state (zoom, track order, feature selection).

Worth revisiting if comparative views become a common notebook target. The shape
is probably:

- make `view_locations` writable, with the JS side navigating each view whose
  entry changed rather than rebuilding (mirroring how `change:location` calls
  `setLocation` in `src/index.ts`)
- separate the hot path from the cold one, the way the single-view widget
  already does: navigation is live, config changes rebuild

The awkward part is identity — `views` is a positional list, so "which view is
this locstring for" is only well-defined while the list is unchanged. A view id
in the `{type, init}` spec would fix that, but it has to agree with whatever
JBrowse's session spec already does.

## Verify the committed bundle in CI

`jbrowse_anywidget/static/*.js` is committed so `pip install` needs no JS
toolchain, which means it can silently drift from `src/`. Nothing catches that
today, and nothing in CI typechecks the TS either.

This was thought to be blocked by the `link:../jbrowse-components` dependency —
`pnpm install` needing a sibling checkout that CI doesn't have. It isn't: CI can
check the monorepo out alongside with `actions/checkout` and a `path:`, install
in it first (the linked packages resolve react/mobx from its tree), then install
and build here. `agent-docs/HANDOFF.md` has the steps.

`pnpm typecheck` also works again as of the `types: []` fix, so a typecheck job
is free. Run the bundle job on a **nightly cron** rather than only push/PR: the
break is normally caused by a monorepo commit, so no event in this repo fires.

Depending on a published version instead, with the monorepo link as an opt-in
override, is still worth doing — it would make the install cheap — but it is no
longer a prerequisite.
