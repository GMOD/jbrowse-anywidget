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

import { changedKeys, defineWidget, report } from './widget'

import type { AnyModel } from '@anywidget/types'

type Options = Omit<CreateAppOptions, 'assemblies' | 'plugins'> & {
  assemblies?: AssemblyInput[]
  plugins?: Parameters<typeof loadPlugins>[0]
}

interface JBrowseAppTraits {
  options: Options
  local_files: NonNullable<CreateAppOptions['localFiles']>
  view_locations: ViewLocation[]
  current_session: unknown
  selected_feature: unknown
}

async function build(el: HTMLElement, model: AnyModel<JBrowseAppTraits>) {
  const {
    assemblies = [],
    tracks,
    aggregateTextSearchAdapters,
    plugins = [],
    ...rest
  } = model.get('options')
  // A hub name brings a track catalog and a search index naming hits by those
  // tracks, so the notebook's own tracks and adapters merge in after the hub's
  const resolved = await resolveAssemblies(assemblies, {
    tracks,
    aggregateTextSearchAdapters,
  })
  return createApp(el, {
    ...rest,
    ...resolved,
    plugins: await loadPlugins(plugins),
    localFiles: model.get('local_files'),
    makeWorkerInstance: () => new RpcWorker(),
    onLocationChange: locations => {
      report(model, 'view_locations', locations)
    },
    onFeatureSelect: feature => {
      report(model, 'selected_feature', feature)
    },
    onSessionChange: session => {
      report(model, 'current_session', session)
    },
  })
}

export default {
  render: defineWidget<JBrowseAppTraits, JBrowseAppController>(
    build,
    ({ controller, rebuild }, model) => {
      let previous = model.get('options')
      return {
        'change:options': () => {
          const next = model.get('options')
          const changed = changedKeys(previous, next)
          previous = next
          if (changed.length === 1 && changed[0] === 'session') {
            controller()?.setSession(next.session ?? undefined)
          } else if (changed.length) {
            rebuild()
          }
        },
      }
    },
  ),
}
