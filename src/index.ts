import '@fontsource/roboto'

import {
  type CreateLinearGenomeViewOptions,
  type LinearGenomeViewController,
  type LinearGenomeViewState,
  createLinearGenomeView,
  loadPlugins,
} from '@jbrowse/react-linear-genome-view2'

import RpcWorker from '@jbrowse/react-linear-genome-view2/esm/rpcWorker?worker&inline'

import {
  type PluginSpec,
  defineWidget,
  report,
  dictOrUndefined,
} from './widget'

import type { AnyModel } from '@anywidget/types'

// The Python-side traits of jbrowse_anywidget.LinearGenomeView, as they arrive
// here. Keep in step with the traitlets declared on that class.
interface LinearGenomeViewTraits {
  assembly: CreateLinearGenomeViewOptions['assembly']
  tracks: NonNullable<CreateLinearGenomeViewOptions['tracks']>
  session: NonNullable<CreateLinearGenomeViewOptions['session']>
  aggregate_text_search_adapters: NonNullable<
    CreateLinearGenomeViewOptions['aggregateTextSearchAdapters']
  >
  plugins: PluginSpec[]
  configuration: NonNullable<CreateLinearGenomeViewOptions['configuration']>
  // name -> bytes; anywidget delivers a Bytes-valued dict as DataViews, which
  // travel as binary buffers rather than JSON
  local_files: NonNullable<CreateLinearGenomeViewOptions['localFiles']>
  location: string
  current_session: unknown
  selected_feature: unknown
}

type Model = AnyModel<LinearGenomeViewTraits>

// Turn the widget's config traits into controller options. Assembly can be a
// hub name string ("hg38") or a config dict; the controller resolves either.
// The loadPlugins records go through whole rather than mapped to `.plugin`,
// since the definition is what lets the RPC worker load the same plugin.
async function optionsFromModel(
  model: Model,
  fail: (e: unknown) => void,
): Promise<CreateLinearGenomeViewOptions> {
  // Awaited before any other trait is read, so a build waiting on a plugin
  // fetch opens whatever the kernel set while it waited. That is what lets the
  // trait handlers below drop an update that arrives with no controller yet:
  // the build in flight is the one that applies it.
  const plugins = await loadPlugins(model.get('plugins'))
  const searchAdapters = model.get('aggregate_text_search_adapters')
  return {
    plugins,
    assembly: model.get('assembly'),
    tracks: model.get('tracks'),
    session: dictOrUndefined(model, 'session'),
    configuration: dictOrUndefined(model, 'configuration'),
    localFiles: model.get('local_files'),
    // Data fetching and parsing run off the notebook's UI thread. Without this
    // the RPC is the main thread, and a deep BAM region blocks the page — the
    // cell, the scroll, and every other widget on it — for as long as the parse
    // takes.
    makeWorkerInstance: () => new RpcWorker(),
    location: model.get('location'),
    aggregateTextSearchAdapters: searchAdapters.length
      ? searchAdapters
      : undefined,
    onError: fail,
    // JS -> Python read-backs, settled by the controller
    onLocationChange: locs => {
      if (model.get('location') !== locs) {
        report(model, 'location', locs)
      }
    },
    onFeatureSelect: feature => {
      report(model, 'selected_feature', feature)
    },
    // The other half of `session`, and deliberately a DIFFERENT trait: the
    // arrangement the user built by hand comes back as the same plain JSON,
    // ready to hand straight back in. Writing it to `session` itself would echo
    // (model.set fires change:session here too) and would override a later
    // change to it.
    onSessionChange: session => {
      report(model, 'current_session', session)
    },
  }
}

export default {
  render: defineWidget<LinearGenomeViewTraits, LinearGenomeViewController>(
    async (el, model, fail) =>
      createLinearGenomeView(el, await optionsFromModel(model, fail)),
    ({ controller, rebuild }, model) => {
      // The controller's one write door, and a declarative one: each field is
      // the complete wanted value, a field left out is left alone, and the
      // engine survives — which is what a notebook needs, because it drives
      // these traits in a loop. 09_interactive_controls sets `view.tracks = []`
      // and then adds one, twice per slider step, and a rebuild each time would
      // re-resolve a remote assembly and start a new RPC worker for a track the
      // user is dragging a slider over.
      const update = (state: LinearGenomeViewState) => {
        controller()
          ?.update(state)
          .catch((e: unknown) => {
            console.error(e)
          })
      }
      return {
        // The genome, the session and the plugins are what the browser is
        // BUILT from — a different genome is a different browser, and a plugin
        // registers view and track types into a live pluginManager — so these
        // destroy the controller and make another. The rest is state, which
        // `update` states in place.
        'change:assembly': rebuild,
        'change:session': rebuild,
        'change:plugins': rebuild,
        // the root config is read once, when the engine is created
        'change:configuration': rebuild,
        'change:tracks': () =>
          // localFiles rides along rather than trusting change:local_files to
          // have run first: a cell that registers a file and opens a track on
          // it changes both traits in one message, and which change event fires
          // first is only state-dict key order. `update` registers the files
          // before it resolves the tracks that name them.
          update({
            localFiles: model.get('local_files'),
            tracks: model.get('tracks'),
          }),
        'change:location': () => update({ location: model.get('location') }),
        // Additive and cheap: registration is keyed on the object the kernel
        // sent, so bytes already registered cost nothing.
        'change:local_files': () =>
          update({ localFiles: model.get('local_files') }),
      }
    },
  ),
}
