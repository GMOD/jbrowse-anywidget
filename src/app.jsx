import '@fontsource/roboto'
import '@jbrowse/react-app2/styles.css'

import { createApp } from '@jbrowse/react-app2'
import { autorun } from 'mobx'

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

// duck-typed like core's isFeature (a feature has get()/id()), inlined so
// app.jsx needs no direct @jbrowse/core import (it's only a transitive dep here)
function isFeature(thing) {
  return (
    typeof thing === 'object' &&
    thing !== null &&
    typeof thing.get === 'function' &&
    typeof thing.id === 'function'
  )
}

// A linear view reports its visible region as a coarseVisibleLocStrings string;
// a comparative view (synteny/dotplot) has no single string, so report the list
// of its sub-views' locstrings instead.
function viewLocation(view) {
  return typeof view.coarseVisibleLocStrings === 'string'
    ? view.coarseVisibleLocStrings || undefined
    : Array.isArray(view.views)
      ? view.views.map(v => v.coarseVisibleLocStrings).filter(Boolean)
      : undefined
}

export default {
  render({ model, el }) {
    let controller
    let disposers = []

    function teardown() {
      for (const dispose of disposers) {
        dispose()
      }
      disposers = []
      controller?.destroy()
    }

    // Build the app and wire the JS -> Python read-backs. Every view's visible
    // region and the selected feature sync to the kernel — the same reactivity
    // the single-view LinearGenomeView widget has, now for synteny/dotplot too.
    function build() {
      controller = createApp(el, optionsFromModel(model))
      const { session } = controller.viewState
      disposers.push(
        autorun(() => {
          model.set('view_locations', session.views.map(viewLocation))
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

    build()

    // config traits are declarative; a change rebuilds the whole app (views are
    // not a hot path like panning, which the autoruns above handle live)
    const rebuild = () => {
      teardown()
      build()
    }
    const events = ['change:assemblies', 'change:tracks', 'change:views']
    for (const event of events) {
      model.on(event, rebuild)
    }

    return () => {
      for (const event of events) {
        model.off(event, rebuild)
      }
      teardown()
    }
  },
}
