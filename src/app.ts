import '@fontsource/roboto'
import '@jbrowse/react-app2/styles.css'

import {
  type AssemblyInput,
  type CreateAppOptions,
  type JBrowseAppController,
  type ViewLocation,
  createApp,
  loadPlugins,
  resolveAssemblies,
} from '@jbrowse/react-app2'

import RpcWorker from '@jbrowse/react-app2/esm/rpcWorker?worker&inline'

import {
  type PluginSpec,
  defineWidget,
  report,
  dictOrUndefined,
} from './widget'

import type { AnyModel } from '@anywidget/types'

// The Python-side traits of jbrowse_anywidget.JBrowseApp, as they arrive here.
// Keep in step with the traitlets declared on that class.
interface JBrowseAppTraits {
  assemblies: AssemblyInput[]
  tracks: CreateAppOptions['tracks']
  views: NonNullable<CreateAppOptions['views']>
  plugins: PluginSpec[]
  configuration: NonNullable<CreateAppOptions['configuration']>
  session: NonNullable<CreateAppOptions['session']>
  local_files: NonNullable<CreateAppOptions['localFiles']>
  view_locations: ViewLocation[]
  current_session: unknown
  selected_feature: unknown
}

type Model = AnyModel<JBrowseAppTraits>

// The widget's traits map straight onto createApp's declarative options:
// assemblies + tracks are config lists, views is the [{type, init}] list that
// reaches synteny/dotplot/circular/etc. Runtime plugins are fetched first, since
// a view type they register has to exist before `views` opens it — and the
// records go through whole rather than mapped to `.plugin`, since the definition
// is what lets the RPC worker load the same plugin.
async function optionsFromModel(model: Model): Promise<CreateAppOptions> {
  // `assemblies` takes the same vocabulary the single-view widget's `assembly`
  // does — a hub name ("hg38"), a sequence URI, a hub config, or a full
  // assembly config. resolveAssemblies is the product's own resolution, which
  // is why the Python side no longer has to fetch a hub itself.
  const { assemblies, aggregateTextSearchAdapters } = await resolveAssemblies(
    model.get('assemblies'),
  )
  return {
    assemblies,
    aggregateTextSearchAdapters,
    tracks: model.get('tracks'),
    localFiles: model.get('local_files'),
    // Data fetching and parsing run off the notebook's UI thread. Without this
    // the RPC is the main thread, and a deep BAM region blocks the page — the
    // cell, the scroll, and every other widget on it — for as long as the parse
    // takes.
    makeWorkerInstance: () => new RpcWorker(),
    views: model.get('views'),
    session: dictOrUndefined(model, 'session'),
    configuration: dictOrUndefined(model, 'configuration'),
    plugins: await loadPlugins(model.get('plugins')),
    onLocationChange: locs => {
      report(model, 'view_locations', locs)
    },
    onFeatureSelect: feature => {
      report(model, 'selected_feature', feature)
    },
    // The other half of `session`, and deliberately a DIFFERENT trait: the
    // arrangement the user built by hand comes back as the same plain JSON,
    // ready to hand straight back in. Writing it to `session` itself would echo
    // (model.set fires change:session here too) and would silently override the
    // `views` a later rebuild is meant to show.
    onSessionChange: session => {
      report(model, 'current_session', session)
    },
  }
}

export default {
  render: defineWidget<JBrowseAppTraits, JBrowseAppController>(
    // createApp is synchronous throughout, so a build that throws — a bad
    // assembly, a plugin that will not fetch — reaches the shell's own catch
    // and the cell shows it. The single-view product needs an onError because
    // its build is asynchronous inside the constructor; this one does not.
    async (el, model) => createApp(el, await optionsFromModel(model)),
    ({ controller, rebuild }, model) => ({
      // config traits are declarative; a change rebuilds the whole app (views
      // are not a hot path like panning, which the read-backs handle live)
      'change:assemblies': rebuild,
      'change:tracks': rebuild,
      'change:views': rebuild,
      'change:plugins': rebuild,
      // the root config is read once, when the engine is created
      'change:configuration': rebuild,
      // a session is state, not config: swapping it in place keeps the engine
      // (and its resolved assemblies and RPC workers) rather than rebuilding
      'change:session': () => {
        controller()?.setSession(dictOrUndefined(model, 'session'))
      },
    }),
  ),
}
