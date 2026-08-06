import type { AnyModel, Render } from '@anywidget/types'

export interface PluginSpec {
  name: string
  url: string
}

interface Controller {
  destroy: () => void
}

export interface WidgetShell<C> {
  /**
   * The live controller, or undefined while a build is in flight. A function
   * rather than a property because a rebuild replaces it: a handler that read a
   * property would be holding whichever one existed when it was registered, and
   * destructuring the shell (which every call site does) would freeze it at
   * `undefined`.
   */
  controller: () => C | undefined
  /** rebuild from the model's current traits; the newest build wins */
  rebuild: () => void
}

/**
 * The shell both widgets sit in: build a controller from the model's traits,
 * let the newest build win, keep the trait handlers registered for the widget's
 * life, and tear everything down on unmount.
 *
 * Building is asynchronous (runtime plugins are fetched), so two builds can be
 * in flight at once — a cell that sets several traits in one go, or a user
 * re-running one. They finish in whatever order their fetches do, not the order
 * they were asked for, so each takes a token and drops itself if a newer one
 * started meanwhile. Without that the last to *finish* wins, and a slow first
 * build can overwrite the state actually asked for.
 */
export function defineWidget<Traits extends object, C extends Controller>(
  build: (el: HTMLElement, model: AnyModel<Traits>) => Promise<C>,
  handlers: (
    shell: WidgetShell<C>,
    model: AnyModel<Traits>,
  ) => Record<string, () => void>,
): Render<Traits> {
  return ({ model, el }) => {
    let controller: C | undefined
    let seq = 0

    function teardown() {
      controller?.destroy()
      controller = undefined
    }

    const rebuild = () => {
      teardown()
      const token = ++seq
      build(el, model)
        .then(built => {
          if (token === seq) {
            controller = built
          } else {
            built.destroy()
          }
        })
        .catch((e: unknown) => {
          console.error(e)
        })
    }

    const registered = handlers(
      { controller: () => controller, rebuild },
      model,
    )
    for (const [event, handler] of Object.entries(registered)) {
      model.on(event, handler)
    }

    rebuild()

    return () => {
      // ++seq first: a build still in flight then loses its token and destroys
      // itself rather than attaching to an unmounted widget
      seq++
      for (const [event, handler] of Object.entries(registered)) {
        model.off(event, handler)
      }
      teardown()
    }
  }
}
