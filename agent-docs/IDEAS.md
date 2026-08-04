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

## Depend on a published @jbrowse/react-app2 instead of the monorepo link

`package.json` uses `link:../jbrowse-components/...`, so building this repo
needs a sibling checkout of the monorepo at a matching commit. That is fine for
a maintainer and a real barrier for anyone else — and it is why CI has to check
the monorepo out alongside, and why a monorepo commit can turn this repo red
with no event here.

Depending on a published version, with the link as an opt-in override, would
make the install cheap. The catch is `resolve.dedupe`: react/mobx resolve out of
whichever tree wins, so a published dep has to pin versions that match what the
embedded product was built against, and the mobx 6-vs-7 break shows how quietly
that goes wrong.

Not urgent. `bundle`, `typecheck` and `render` all cover the drift this was
originally about.
