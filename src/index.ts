import '@fontsource/roboto'

import {
  type CreateLinearGenomeViewOptions,
  type LinearGenomeViewController,
  createLinearGenomeView,
  loadPlugins,
} from '@jbrowse/react-linear-genome-view2'

import type { AnyModel, Render } from '@anywidget/types'

// The Python-side traits of jbrowse_anywidget.LinearGenomeView, as they arrive
// here. Keep in step with the traitlets declared on that class.
interface LinearGenomeViewTraits {
  assembly: CreateLinearGenomeViewOptions['assembly']
  tracks: NonNullable<CreateLinearGenomeViewOptions['tracks']>
  default_session: NonNullable<CreateLinearGenomeViewOptions['defaultSession']>
  aggregate_text_search_adapters: NonNullable<
    CreateLinearGenomeViewOptions['aggregateTextSearchAdapters']
  >
  plugins: { name: string; url: string }[]
  location: string
  selected_feature: unknown
}

type Model = AnyModel<LinearGenomeViewTraits>

function hasSession(model: Model) {
  return Object.keys(model.get('default_session')).length > 0
}

function sessionOrUndefined(model: Model) {
  return hasSession(model) ? model.get('default_session') : undefined
}

// Turn the widget's config traits into controller options. Assembly can be a
// hub name string ("hg38") or a config dict; the controller resolves either.
async function optionsFromModel(model: Model) {
  const searchAdapters = model.get('aggregate_text_search_adapters')
  const plugins = model.get('plugins')
  const loaded = plugins.length ? await loadPlugins(plugins) : []
  return {
    plugins: loaded.map(p => p.plugin),
    assembly: model.get('assembly'),
    tracks: model.get('tracks'),
    defaultSession: sessionOrUndefined(model),
    location: model.get('location'),
    aggregateTextSearchAdapters: searchAdapters.length
      ? searchAdapters
      : undefined,
    // JS -> Python read-backs (same autorun mechanism the location trait uses)
    onLocationChange: (locs: string) => {
      if (model.get('location') !== locs) {
        model.set('location', locs)
        model.save_changes()
      }
    },
    onFeatureSelect: (feature: unknown) => {
      model.set('selected_feature', feature)
      model.save_changes()
    },
  }
}

const render: Render<LinearGenomeViewTraits> = ({ model, el }) => {
  // fetching runtime plugins makes creation asynchronous, so the controller
  // only exists once they resolve; `destroyed` covers a widget torn down
  // before that lands. Plugins are fixed at creation (they register view and
  // track types into a live pluginManager), so unlike the other traits a
  // change to `plugins` rebuilds nothing — remake the widget.
  let controller: LinearGenomeViewController | undefined
  let destroyed = false

  const handlers = {
    'change:assembly': () => controller?.setAssembly(model.get('assembly')),
    'change:default_session': () =>
      controller?.setSession(sessionOrUndefined(model)),
    'change:tracks': () => controller?.setTracks(model.get('tracks')),
    'change:location': () => {
      controller?.setLocation(model.get('location')).catch((e: unknown) => {
        console.error(e)
      })
    },
  }

  optionsFromModel(model)
    .then(options => {
      if (!destroyed) {
        controller = createLinearGenomeView(el, options)
      }
    })
    .catch((e: unknown) => {
      console.error(e)
    })

  for (const [event, handler] of Object.entries(handlers)) {
    model.on(event, handler)
  }

  return () => {
    destroyed = true
    for (const [event, handler] of Object.entries(handlers)) {
      model.off(event, handler)
    }
    controller?.destroy()
  }
}

export default { render }
