import '@fontsource/roboto'

import {
  type CreateLinearGenomeViewOptions,
  type LinearGenomeViewController,
  createLinearGenomeView,
  loadPlugins,
} from '@jbrowse/react-linear-genome-view2'

import { type PluginSpec, defineWidget } from './widget'

import type { AnyModel } from '@anywidget/types'

// The Python-side traits of jbrowse_anywidget.LinearGenomeView, as they arrive
// here. Keep in step with the traitlets declared on that class.
interface LinearGenomeViewTraits {
  assembly: CreateLinearGenomeViewOptions['assembly']
  tracks: NonNullable<CreateLinearGenomeViewOptions['tracks']>
  default_session: NonNullable<CreateLinearGenomeViewOptions['defaultSession']>
  aggregate_text_search_adapters: NonNullable<
    CreateLinearGenomeViewOptions['aggregateTextSearchAdapters']
  >
  plugins: PluginSpec[]
  // name -> bytes; anywidget delivers a Bytes-valued dict as DataViews, which
  // travel as binary buffers rather than JSON
  local_files: NonNullable<CreateLinearGenomeViewOptions['localFiles']>
  location: string
  selected_feature: unknown
}

type Model = AnyModel<LinearGenomeViewTraits>

// An empty dict is the trait's "unset"
function sessionOrUndefined(model: Model) {
  const session = model.get('default_session')
  return Object.keys(session).length > 0 ? session : undefined
}

// Turn the widget's config traits into controller options. Assembly can be a
// hub name string ("hg38") or a config dict; the controller resolves either.
// The loadPlugins records go through whole rather than mapped to `.plugin`,
// since the definition is what lets the RPC worker load the same plugin.
async function optionsFromModel(
  model: Model,
): Promise<CreateLinearGenomeViewOptions> {
  const searchAdapters = model.get('aggregate_text_search_adapters')
  return {
    plugins: await loadPlugins(model.get('plugins')),
    assembly: model.get('assembly'),
    tracks: model.get('tracks'),
    defaultSession: sessionOrUndefined(model),
    localFiles: model.get('local_files'),
    location: model.get('location'),
    aggregateTextSearchAdapters: searchAdapters.length
      ? searchAdapters
      : undefined,
    // JS -> Python read-backs, settled by the controller
    onLocationChange: locs => {
      if (model.get('location') !== locs) {
        model.set('location', locs)
        model.save_changes()
      }
    },
    onFeatureSelect: feature => {
      model.set('selected_feature', feature)
      model.save_changes()
    },
  }
}

export default {
  render: defineWidget<LinearGenomeViewTraits, LinearGenomeViewController>(
    async (el, model) =>
      createLinearGenomeView(el, await optionsFromModel(model)),
    ({ controller, rebuild }, model) => {
      // registering is idempotent per name, so calling this more than once is free
      const syncLocalFiles = () => {
        controller()?.addLocalFiles(model.get('local_files'))
      }
      return {
        'change:assembly': () => {
          controller()?.setAssembly(model.get('assembly'))
        },
        'change:default_session': () => {
          controller()?.setSession(sessionOrUndefined(model))
        },
        'change:local_files': syncLocalFiles,
        'change:tracks': () => {
          // sync files FIRST rather than trusting change:local_files to have
          // run: a cell that registers a file and opens a track on it changes
          // both traits in one message, and which change event fires first is
          // only state-dict key order
          syncLocalFiles()
          controller()?.setTracks(model.get('tracks'))
        },
        'change:location': () => {
          controller()
            ?.setLocation(model.get('location'))
            .catch((e: unknown) => {
              console.error(e)
            })
        },
        // plugins register view and track types into a live pluginManager, so
        // unlike every other trait a change here cannot be applied in place
        'change:plugins': rebuild,
      }
    },
  ),
}
