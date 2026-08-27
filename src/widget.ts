import type { AnyModel, Render } from '@anywidget/types'

export interface PluginSpec {
  name: string
  url: string
}

interface Controller {
  destroy: () => void
}

type Traits = Record<string, any>

/** Push one trait to the kernel. Every JS -> Python read-back is this shape. */
export function report<T extends Traits, K extends keyof T>(
  model: AnyModel<T>,
  trait: K,
  value: T[K],
) {
  model.set(trait, value)
  model.save_changes()
}

/**
 * An empty dict is the `session` trait's "unset". Shared by both widgets: a
 * traitlets Dict has no null, so the products' `undefined` — open the declared
 * views/tracks instead — has to be spelled some other way on the wire.
 */
export function sessionOrUndefined<T extends Traits & { session: object }>(
  model: AnyModel<T>,
) {
  const session = model.get('session')
  return session && Object.keys(session).length > 0 ? session : undefined
}

const ERROR_CLASS = 'jbrowse-anywidget-error'

// A failed build otherwise leaves an empty output cell with the reason only in
// the browser's devtools console — which a notebook user has no reason to have
// open, and which the kernel never sees.
function showError(el: HTMLElement, e: unknown) {
  const box = document.createElement('pre')
  box.className = ERROR_CLASS
  box.style.cssText =
    'margin:0;padding:8px;overflow:auto;white-space:pre-wrap;' +
    'font-family:monospace;font-size:12px;color:#a00;background:#fff5f5;' +
    'border:1px solid #a00;box-sizing:border-box'
  box.textContent = `JBrowse failed to render\n\n${e instanceof Error ? (e.stack ?? e.message) : String(e)}`
  el.append(box)
}

function clearError(el: HTMLElement) {
  for (const node of el.querySelectorAll(`.${ERROR_CLASS}`)) {
    node.remove()
  }
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
 *
 * `build` gets a `fail` callback to hand the products their `onError`. Their
 * own build is asynchronous *inside* the constructor, so a genome that will not
 * resolve never reaches the promise this awaits — without passing it on, that
 * failure reaches only the console and the cell stays blank.
 */
export function defineWidget<Traits extends object, C extends Controller>(
  build: (
    el: HTMLElement,
    model: AnyModel<Traits>,
    fail: (e: unknown) => void,
  ) => Promise<C>,
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
      clearError(el)
      const token = ++seq
      const fail = (e: unknown) => {
        console.error(e)
        if (token === seq) {
          showError(el, e)
        }
      }
      build(el, model, fail)
        .then(built => {
          if (token === seq) {
            controller = built
          } else {
            built.destroy()
          }
        })
        .catch(fail)
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
