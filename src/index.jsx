import '@fontsource/roboto'

import {
  JBrowseLinearGenomeView,
  createViewState,
} from '@jbrowse/react-linear-genome-view2'
import { autorun } from 'mobx'
import { createElement, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'

function hasSession(model) {
  return Object.keys(model.get('default_session')).length > 0
}

// Build a fresh MST view state from the widget's config traits. Rebuilt only
// when assembly or default_session changes; track additions are applied
// incrementally by syncTracks so adding a track doesn't remount the view.
function buildViewState(model) {
  const assembly = model.get('assembly')
  const state = createViewState({
    assembly,
    tracks: model.get('tracks'),
    defaultSession: hasSession(model) ? model.get('default_session') : undefined,
  })
  // Route navigation through setInit (same path as the managed component) so
  // the view shows a spinner while the assembly loads rather than the import
  // form. A default_session already positions the view, so only navigate when
  // there isn't one. Track opening is handled separately by syncTracks.
  if (!hasSession(model)) {
    const location = model.get('location')
    state.session.view.setInit({
      assembly: assembly.name,
      loc: location ? location : undefined,
    })
  }
  return state
}

// Open every configured track and close any that Python removed from the list.
// showTrack/addTrackConf both dedupe by trackId, so this is safe to run on
// mount and on every tracks change. A default_session owns visibility itself,
// so leave its layout untouched when one is present.
function syncTracks(model, state) {
  if (!hasSession(model)) {
    const { session } = state
    const { view } = session
    const tracks = model.get('tracks')
    const wanted = new Set(tracks.map(t => t.trackId))
    for (const conf of tracks) {
      session.addTrackConf(conf)
      view.showTrack(conf.trackId)
    }
    for (const track of [...view.tracks]) {
      const trackId = track.configuration.trackId
      if (!wanted.has(trackId)) {
        view.hideTrack(trackId)
      }
    }
  }
}

function View({ model }) {
  const [state, setState] = useState(() => buildViewState(model))

  // Config traits that require a full rebuild of the view state
  useEffect(() => {
    const rebuild = () => setState(buildViewState(model))
    model.on('change:assembly', rebuild)
    model.on('change:default_session', rebuild)
    return () => {
      model.off('change:assembly', rebuild)
      model.off('change:default_session', rebuild)
    }
  }, [model])

  // Open/close tracks incrementally on mount and whenever the list changes
  useEffect(() => {
    syncTracks(model, state)
    const onTracks = () => syncTracks(model, state)
    model.on('change:tracks', onTracks)
    return () => model.off('change:tracks', onTracks)
  }, [model, state])

  // Python -> JS navigation. Guard against the JS->Python echo below by only
  // navigating when the requested location differs from what's already shown.
  useEffect(() => {
    const view = state.session.view
    const onLocation = () => {
      const loc = model.get('location')
      if (loc && view.coarseVisibleLocStrings !== loc) {
        view.navToLocString(loc).catch(e => {
          console.error(e)
        })
      }
    }
    model.on('change:location', onLocation)
    return () => model.off('change:location', onLocation)
  }, [model, state])

  // JS -> Python: mirror the current (throttled) visible region back to Python
  useEffect(() => {
    const view = state.session.view
    const dispose = autorun(() => {
      const locs = view.coarseVisibleLocStrings
      if (locs && model.get('location') !== locs) {
        model.set('location', locs)
        model.save_changes()
      }
    })
    return () => dispose()
  }, [model, state])

  return createElement(JBrowseLinearGenomeView, { viewState: state })
}

export default {
  render({ model, el }) {
    const root = createRoot(el)
    root.render(createElement(View, { model }))
    return () => root.unmount()
  },
}
