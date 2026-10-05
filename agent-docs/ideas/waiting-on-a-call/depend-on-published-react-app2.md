---
name: depend-on-published-react-app2
description: Replace the link: dependency on the monorepo with a published @jbrowse/react-app2, so installing needs no sibling checkout.
---

# Depend on a published @jbrowse/react-app2 instead of the monorepo link

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

`origin/main` sat four commits behind the maintainer's checkout, so every
scheduled run tested `f7a9c88` — a tree whose `src/index.ts` still called
`setAssembly`/`setSession`/`setTracks`, which upstream dropped in `aaeb2fae55`
on 2026-08-06. Read off the run list: the last green nightly was 2026-08-06, and
2026-08-07 through 2026-08-26 is **twenty consecutive failures**. On the first
of them `typecheck` was the only red job — `bundle` passed, which is "esbuild
does not typecheck" demonstrated rather than argued. `ffb7006` had already fixed
exactly that break, on 2026-08-06 itself, and was never pushed: twenty nights of
red reporting a failure that no longer existed anywhere but on origin.

Meanwhile the local tree broke on its own, invisibly to those jobs: `0c999fe484`
turned the remaining four setters into one `update()` on 2026-08-18, and the
widget's track, location and local-file handlers were dead at runtime until
2026-08-26.

So neither gap is coverage. One is that nothing carried twenty red nights to
anyone; the other is that the tree CI tests and the tree the maintainer builds
had drifted apart. A published dep would change neither.
