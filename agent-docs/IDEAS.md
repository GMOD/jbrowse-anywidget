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
  entry changed rather than rebuilding (mirroring how `change:location` states
  `update({location})` in `src/index.ts`)
- separate the hot path from the cold one, the way the single-view widget
  already does: navigation is live, config changes rebuild

This used to say the awkward part is identity — `views` is positional, so "which
view is this locstring for" is only well-defined while the list is unchanged,
and a view id in the spec would have to agree with JBrowse's own. **It already
does**: `ManagedView` carries an optional `id`, and `viewsToSession` opens each
view as `view.id ?? 'view-<i>'`, so a spec that names its views has stable ids
in the live session to navigate by. What is left is the navigation itself —
`JBrowseAppController` has no per-view door, only `addView`/`removeView`/
`setSession`, so this reaches through its `viewState` or wants an upstream one.

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

Not urgent — but not for the reason this used to give, which was that `bundle`,
`typecheck` and `render` cover the drift. They detect it. What went wrong by
2026-08-26 was upstream of that, twice over.

`origin/main` was four commits behind the maintainer's checkout, so every
scheduled run for twenty days tested `f7a9c88` — a tree whose `src/index.ts`
still called `setAssembly`/`setSession`/`setTracks`, dropped upstream on
2026-08-06. `typecheck` was red from that day, `render` from 2026-08-07 when the
readiness waits moved to `@jbrowse/capture`. `ffb7006` had fixed the first of
those on 2026-08-06 itself and was never pushed, so the jobs kept reporting a
break that was already repaired on a laptop.

Meanwhile the local tree broke on its own: `0c999fe484` turned the remaining
four setters into one `update()` on 2026-08-18, and the widget's track, location
and local-file handlers were dead at runtime until 2026-08-26.

So neither gap is coverage. One is that nothing carried three red jobs to
anyone; the other is that the repo CI tests and the repo the maintainer builds
were different trees. A published dep would change neither.
