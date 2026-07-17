import '@fontsource/roboto'
import '@jbrowse/react-app2/styles.css'

import { createApp } from '@jbrowse/react-app2'

// The multi-view widget's traits map straight onto createApp's declarative
// options: assemblies + tracks are config lists, views is the [{type, init}]
// list that reaches synteny/dotplot/circular/etc.
function optionsFromModel(model) {
  return {
    assemblies: model.get('assemblies'),
    tracks: model.get('tracks'),
    views: model.get('views'),
  }
}

export default {
  render({ model, el }) {
    let controller = createApp(el, optionsFromModel(model))

    // a multi-view session is described up front; a change to any of the
    // config traits rebuilds the whole app (simplest correct behavior — these
    // are not hot paths like LGV panning)
    const rebuild = () => {
      controller.destroy()
      controller = createApp(el, optionsFromModel(model))
    }
    const events = ['change:assemblies', 'change:tracks', 'change:views']
    for (const event of events) {
      model.on(event, rebuild)
    }

    return () => {
      for (const event of events) {
        model.off(event, rebuild)
      }
      controller.destroy()
    }
  },
}
