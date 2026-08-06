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

// The track list each live engine is currently showing. `change:tracks` diffs
// against it rather than re-applying the whole list, because a notebook drives
// that trait in a loop: 09_interactive_controls sets `view.tracks = []` and then
// adds one, twice per slider step, and a rebuild each time would re-resolve a
// remote assembly and start a new RPC worker for a track the user is dragging a
// slider over.
//
// Keyed by model rather than held in a closure: `defineWidget` takes the build
// and the handlers once, at module scope, and calls them per rendered widget —
// so a plain variable here would be shared by two views in one notebook.
const appliedTracks = new WeakMap<Model, LinearGenomeViewTraits['tracks']>()

// Diffing needs a name for each entry, and a loose spec (a bare URL the view
// expands) has none until the engine resolves it. So the fast path is taken
// only when every entry on both sides carries a trackId; anything else rebuilds,
// which is always correct and is what changing the genome does anyway.
function trackIds(tracks: LinearGenomeViewTraits['tracks']) {
  const ids = tracks.map(track =>
    track && typeof track === 'object' && 'trackId' in track
      ? (track.trackId as string)
      : undefined,
  )
  return ids.every(id => id !== undefined) ? (ids as string[]) : undefined
}

export default {
  render: defineWidget<LinearGenomeViewTraits, LinearGenomeViewController>(
    async (el, model) => {
      // whatever this build is about to open is what a later diff starts from
      appliedTracks.set(model, model.get('tracks'))
      return createLinearGenomeView(el, await optionsFromModel(model))
    },
    ({ controller, rebuild }, model) => {
      // registering is idempotent per name, so calling this more than once is free
      const syncLocalFiles = () => {
        controller()?.addLocalFiles(model.get('local_files'))
      }
      return {
        // Config traits rebuild, the same rule the app widget follows. The
        // genome, the session and the track list are what the browser is built
        // from, and the controller no longer offers a setter for any of them:
        // its setAssembly/setSession were `destroy and build again` spelled as
        // methods, and setTracks reconciled a list the user may have opened
        // their own tracks into. Rebuilding here is what those did, minus a
        // controller API per trait.
        'change:assembly': rebuild,
        'change:default_session': rebuild,
        // Expressed with addTrack/removeTrack rather than a controller-side
        // bulk setter, which is both smaller upstream and better behaved: only
        // tracks the notebook itself declared are closed, so one the *user*
        // opened by hand survives a re-run. The old setTracks closed it.
        'change:tracks': () => {
          // sync files FIRST rather than trusting change:local_files to have
          // run: a cell that registers a file and opens a track on it changes
          // both traits in one message, and which change event fires first is
          // only state-dict key order
          syncLocalFiles()
          const next = model.get('tracks')
          const before = trackIds(appliedTracks.get(model) ?? [])
          const after = trackIds(next)
          const live = controller()
          // Mid-build there is nothing to diff against and nothing to call: the
          // build in flight read the trait when it started, so it is opening the
          // PREVIOUS list. Rebuilding is what picks up this one — the stale
          // build loses its token and destroys the engine it was making.
          if (!before || !after || !live) {
            rebuild()
            return
          }
          for (const id of before.filter(id => !after.includes(id))) {
            live.removeTrack(id)
          }
          for (const [i, id] of after.entries()) {
            if (!before.includes(id)) {
              live.addTrack(next[i]!)
            }
          }
          appliedTracks.set(model, next)
        },
        // plugins register view and track types into a live pluginManager, so
        // this one could never have been applied in place either
        'change:plugins': rebuild,
        // The hot path, which is why it is not a rebuild: panning is the
        // interaction that repeats, and a notebook driving `location` from a
        // slider would otherwise refetch the tracks on every step.
        'change:location': () => {
          controller()
            ?.setLocation(model.get('location'))
            .catch((e: unknown) => {
              console.error(e)
            })
        },
        // Additive and cheap: registration is keyed on the object the kernel
        // sent, so bytes already registered cost nothing, and a rebuild does
        // not re-register them either.
        'change:local_files': syncLocalFiles,
      }
    },
  ),
}
