import '@fontsource/roboto'

import { createLinearGenomeView } from '@jbrowse/react-linear-genome-view2'

function hasSession(model) {
  return Object.keys(model.get('default_session')).length > 0
}

function sessionOrUndefined(model) {
  return hasSession(model) ? model.get('default_session') : undefined
}

// Turn the widget's config traits into controller options. Assembly can be a
// hub name string ("hg38") or a config dict; the controller resolves either.
function optionsFromModel(model) {
  const searchAdapters = model.get('aggregate_text_search_adapters')
  return {
    assembly: model.get('assembly'),
    tracks: model.get('tracks'),
    defaultSession: sessionOrUndefined(model),
    location: model.get('location'),
    aggregateTextSearchAdapters: searchAdapters.length
      ? searchAdapters
      : undefined,
    // JS -> Python read-backs (same autorun mechanism the location trait uses)
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
  render({ model, el }) {
    const controller = createLinearGenomeView(el, optionsFromModel(model))

    const handlers = {
      'change:assembly': () => controller.setAssembly(model.get('assembly')),
      'change:default_session': () =>
        controller.setSession(sessionOrUndefined(model)),
      'change:tracks': () => controller.setTracks(model.get('tracks')),
      'change:location': () => {
        controller.setLocation(model.get('location')).catch(e => {
          console.error(e)
        })
      },
    }
    for (const [event, handler] of Object.entries(handlers)) {
      model.on(event, handler)
    }

    return () => {
      for (const [event, handler] of Object.entries(handlers)) {
        model.off(event, handler)
      }
      controller.destroy()
    }
  },
}
