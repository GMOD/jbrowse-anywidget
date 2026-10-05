---
name: jbrowseapp-write-once-from-python
description: JBrowseApp has no Python-to-view navigation: view_locations is read-back only and every config trait rebuilds the app, losing view state.
---

# JBrowseApp is write-once from Python

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
