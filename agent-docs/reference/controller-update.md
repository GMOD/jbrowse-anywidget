# The controller takes one declarative `update()`

`LinearGenomeViewController` is now `whenReady` / `update(state)` / `destroy`.
The four setters this repo used to call — `addTrack`, `removeTrack`,
`setLocation`, `addLocalFiles` — are gone (upstream `0c999fe484`), and before
that `setAssembly`/`setSession`/`setTracks` went the same way. `update` takes
`{ tracks?, location?, localFiles? }`: each field you state is the complete
wanted value, a field you leave out is left alone, and the engine survives.

What that means here: `change:assembly`, `change:session` and `change:plugins`
call the shell's `rebuild` — a different genome is a different browser, and a
plugin registers types into a live pluginManager. Everything else is one
`update` call, and **the trackId diff that used to live in `src/index.ts` is
gone**: no `appliedTracks` WeakMap, no `trackIds`, no rebuild fallback. The
controller reconciles the wanted list against what is open, `guessTrackConf`
expands a loose spec on the way, so the loose-spec case that used to force a
rebuild now updates live like any other.

Two things follow that are easy to get wrong:

- **`change:tracks` states `localFiles` too**, rather than trusting
  `change:local_files` to have run first. A cell that registers a file and opens
  a track on it changes both traits in one message and the event order is only
  state-dict key order; `update` registers files before it resolves the tracks
  that name them.
- **`optionsFromModel` awaits `loadPlugins` before reading any other trait.** A
  build waiting on a plugin fetch then opens whatever the kernel set while it
  waited — which is what lets the handlers drop an `update` that arrives with no
  controller yet instead of needing a rebuild fallback.

**A build failure needs `onError`.** `createLinearGenomeView` returns
synchronously and resolves the assembly inside itself, so a genome that will not
resolve never reaches the promise `defineWidget` awaits. `defineWidget` hands
`build` a `fail` callback for exactly this; without it the cell stays blank and
the reason is console-only. `createApp` is synchronous throughout and needs
none.

`scripts/verify_bundle_runtime.mjs` covers it in a real browser, on the nightly
render workflow. Note what it does NOT assert: DOM node identity. React
legitimately replaces the header's nodes when the track list changes, so an
identity check reads as a rebuild that never happened — it counts container
unmounts instead. That cost a debugging round; don't reintroduce it.
