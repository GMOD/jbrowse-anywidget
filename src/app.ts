import '@fontsource/roboto'
import '@jbrowse/react-app2/styles.css'

import {
  type CreateAppOptions,
  type JBrowseAppController,
  createApp,
  getSessionSnapshot,
  loadPlugins,
} from '@jbrowse/react-app2'
import { autorun, untracked } from 'mobx'

import type { AnyModel, Render } from '@anywidget/types'

// The Python-side traits of jbrowse_anywidget.JBrowseApp, as they arrive here.
// Keep in step with the traitlets declared on that class.
interface JBrowseAppTraits {
  assemblies: CreateAppOptions['assemblies']
  tracks: CreateAppOptions['tracks']
  views: NonNullable<CreateAppOptions['views']>
  plugins: { name: string; url: string }[]
  session: NonNullable<CreateAppOptions['session']>
  view_locations: (string | string[] | undefined)[]
  current_session: unknown
  selected_feature: unknown
}

type Model = AnyModel<JBrowseAppTraits>

// The multi-view widget's traits map straight onto createApp's declarative
// options: assemblies + tracks are config lists, views is the [{type, init}]
// list that reaches synteny/dotplot/circular/etc. Runtime plugins are fetched
// first, since a view type they register has to exist before `views` opens it.
async function optionsFromModel(model: Model) {
  const plugins = model.get('plugins')
  const loaded = plugins.length ? await loadPlugins(plugins) : []
  return {
    assemblies: model.get('assemblies'),
    tracks: model.get('tracks'),
    views: model.get('views'),
    session: sessionOrUndefined(model),
    plugins: loaded.map(p => p.plugin),
  }
}

// An empty dict is the trait's "unset": the app then opens the `views` it was
// declared with, which is also where setSession(undefined) returns it to.
function sessionOrUndefined(model: Model) {
  const session = model.get('session')
  return session && Object.keys(session).length > 0 ? session : undefined
}

interface MaybeFeature {
  get?: unknown
  id?: unknown
  toJSON?: () => unknown
}

// duck-typed like core's isFeature (a feature has get()/id()), inlined so
// app.ts needs no direct @jbrowse/core import (it's only a transitive dep here)
function isFeature(
  thing: unknown,
): thing is MaybeFeature & { toJSON: () => unknown } {
  const feature = thing as MaybeFeature | null
  return (
    typeof feature === 'object' &&
    feature !== null &&
    typeof feature.get === 'function' &&
    typeof feature.id === 'function'
  )
}

interface MaybeComparativeView {
  coarseVisibleLocStrings?: string
  views?: { coarseVisibleLocStrings?: string }[]
}

// A linear view reports its visible region as a coarseVisibleLocStrings string;
// a comparative view (synteny/dotplot) has no single string, so report the list
// of its sub-views' locstrings instead.
function viewLocation(view: MaybeComparativeView) {
  return typeof view.coarseVisibleLocStrings === 'string'
    ? view.coarseVisibleLocStrings || undefined
    : view.views
      ? view.views
          .map(v => v.coarseVisibleLocStrings)
          .filter(loc => loc !== undefined)
      : undefined
}

interface MaybeSession {
  views: (MaybeComparativeView & {
    id?: string
    tracks?: { configuration: { trackId: string } }[]
  })[]
}

// The signal the session read-back rides on: which views exist, what each has
// open, and where each is looking. Deliberately NOT the whole snapshot —
// reading that would make the autorun depend on offsetPx, and a snapshot is
// kilobytes, so a drag would push one per pointer event through the comm.
// coarseVisibleLocStrings is JBrowse's own debounced (500ms) location, so this
// settles after a pan rather than firing during it.
function layoutSignal(session: MaybeSession) {
  return session.views
    .map(
      view =>
        `${view.id}:${JSON.stringify(viewLocation(view))}:${(view.tracks ?? [])
          .map(t => t.configuration.trackId)
          .join(',')}`,
    )
    .join('|')
}

const render: Render<JBrowseAppTraits> = ({ model, el }) => {
  let controller: JBrowseAppController | undefined
  let disposers: (() => void)[] = []
  // plugin loading makes a build asynchronous, so a rebuild that lands while
  // one is in flight has to win: each build takes a token and drops itself if
  // a newer one started meanwhile
  let seq = 0

  function teardown() {
    for (const dispose of disposers) {
      dispose()
    }
    disposers = []
    controller?.destroy()
    controller = undefined
  }

  // Build the app and wire the JS -> Python read-backs. Every view's visible
  // region and the selected feature sync to the kernel — the same reactivity
  // the single-view LinearGenomeView widget has, now for synteny/dotplot too.
  async function build() {
    const token = ++seq
    const options = await optionsFromModel(model)
    if (token !== seq) {
      return
    }
    controller = createApp(el, options)
    const { session } = controller.viewState
    const { viewState } = controller
    disposers.push(
      autorun(() => {
        model.set('view_locations', session.views.map(viewLocation))
        // The other half of `session`, and deliberately a DIFFERENT trait: the
        // arrangement the user built by hand comes back as the same plain JSON,
        // ready to hand straight back in. Writing it to `session` itself would
        // echo (model.set fires change:session here too) and would silently
        // override the `views` a later rebuild is meant to show.
        //
        // untracked so the snapshot read adds no dependencies — layoutSignal is
        // what decides when this runs.
        layoutSignal(session)
        model.set(
          'current_session',
          untracked(() => getSessionSnapshot(viewState)),
        )
        model.save_changes()
      }),
    )
    disposers.push(
      autorun(() => {
        const { selection } = session
        if (isFeature(selection)) {
          model.set('selected_feature', selection.toJSON())
          model.save_changes()
        }
      }),
    )
  }

  const rebuild = () => {
    teardown()
    build().catch((e: unknown) => {
      console.error(e)
    })
  }

  rebuild()

  // config traits are declarative; a change rebuilds the whole app (views are
  // not a hot path like panning, which the autoruns above handle live)
  // a session is state, not config: swapping it in place keeps the engine (and
  // its resolved assemblies and RPC workers) rather than rebuilding
  const restore = () => {
    controller?.setSession(sessionOrUndefined(model))
  }
  const handlers: Record<string, () => void> = {
    'change:assemblies': rebuild,
    'change:tracks': rebuild,
    'change:views': rebuild,
    'change:plugins': rebuild,
    'change:session': restore,
  }
  for (const [event, handler] of Object.entries(handlers)) {
    model.on(event, handler)
  }

  return () => {
    for (const [event, handler] of Object.entries(handlers)) {
      model.off(event, handler)
    }
    teardown()
  }
}

export default { render }
