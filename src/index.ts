import '@fontsource/roboto'

import {
  type CreateLinearGenomeViewOptions,
  type LinearGenomeViewController,
  createLinearGenomeView,
  loadPlugins,
} from '@jbrowse/react-linear-genome-view2'

import RpcWorker from '@jbrowse/react-linear-genome-view2/esm/rpcWorker?worker&inline'

import { changedKeys, defineWidget, report, resolveAgainstPage } from './widget'

import type { AnyModel } from '@anywidget/types'

type Options = Omit<CreateLinearGenomeViewOptions, 'plugins'> & {
  plugins?: Parameters<typeof loadPlugins>[0]
}

interface LinearGenomeViewTraits {
  options: Options
  local_files: NonNullable<CreateLinearGenomeViewOptions['localFiles']>
  location: string
  current_session: unknown
  selected_feature: unknown
}

const LIVE = new Set(['tracks', 'location'])

async function build(
  el: HTMLElement,
  model: AnyModel<LinearGenomeViewTraits>,
  fail: (e: unknown) => void,
) {
  // options are read after the plugin fetch, so a live update that lands while
  // it waits, with no controller to receive it, still reaches this build
  const plugins = await loadPlugins(model.get('options').plugins ?? [])
  return createLinearGenomeView(el, {
    ...resolveAgainstPage(model.get('options')),
    plugins,
    localFiles: model.get('local_files'),
    makeWorkerInstance: () => new RpcWorker(),
    onError: fail,
    onLocationChange: location => {
      if (model.get('location') !== location) {
        report(model, 'location', location)
      }
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
  render: defineWidget<LinearGenomeViewTraits, LinearGenomeViewController>(
    build,
    ({ controller, rebuild }, model) => {
      let previous = model.get('options')
      const update = (
        state: Parameters<LinearGenomeViewController['update']>[0],
      ) => {
        controller()
          ?.update(state)
          .catch((e: unknown) => {
            console.error(e)
          })
      }
      return {
        'change:options': () => {
          const next = model.get('options')
          const changed = changedKeys(previous, next)
          previous = next
          if (!changed.length) {
            return
          }
          if (changed.every(key => LIVE.has(key))) {
            // localFiles rides along: a cell that registers a file and opens a
            // track on it sends both, in an order this handler cannot rely on
            update({
              localFiles: model.get('local_files'),
              ...Object.fromEntries(
                changed.map(key => [
                  key,
                  resolveAgainstPage(next[key as keyof Options]),
                ]),
              ),
            })
          } else {
            rebuild()
          }
        },
        'change:local_files': () => {
          update({ localFiles: model.get('local_files') })
        },
      }
    },
  ),
}
