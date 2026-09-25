/**
 * Base class for every interactive piece of the site.
 *
 * Contract
 * --------
 * - `static selector` is the CSS selector the App uses to find instances.
 * - `mount()` is where a subclass wires itself up. It must be safe to call
 *   exactly once, and it must never throw for a reason the visitor can cause.
 * - Listeners registered via `this.on()` are released by `destroy()`, so a
 *   component can be torn down without leaking handlers.
 *
 * Nothing here assumes the component is essential: the markup it enhances is
 * expected to be usable on its own (progressive enhancement).
 */
export class Component {
  /** @type {string|null} */
  static selector = null;

  /**
   * @param {HTMLElement} element  root element of this instance
   * @param {{bus?: import('./EventBus.js').EventBus, store?: import('./Store.js').Store}} [context]
   */
  constructor(element, context = {}) {
    if (!(element instanceof HTMLElement)) {
      throw new TypeError(`${this.constructor.name}: element is required`);
    }

    this.el = element;
    this.bus = context.bus ?? null;
    this.store = context.store ?? null;
    this.mounted = false;

    /** @type {Array<{target: EventTarget, type: string, handler: Function, options: any}>} */
    this._bindings = [];
  }

  /** Subclasses override. */
  mount() {}

  /** Release every listener this component registered. */
  destroy() {
    for (const { target, type, handler, options } of this._bindings) {
      target.removeEventListener(type, handler, options);
    }
    this._bindings.length = 0;
    this.mounted = false;
  }

  /**
   * Add a tracked event listener.
   * @returns {() => void} an unbind function
   */
  on(target, type, handler, options) {
    const bound = handler.bind(this);
    target.addEventListener(type, bound, options);
    const binding = { target, type, handler: bound, options };
    this._bindings.push(binding);

    return () => {
      target.removeEventListener(type, bound, options);
      const i = this._bindings.indexOf(binding);
      if (i > -1) this._bindings.splice(i, 1);
    };
  }

  /** Scoped query helpers. */
  $(selector) { return this.el.querySelector(selector); }
  $$(selector) { return Array.from(this.el.querySelectorAll(selector)); }

  /** Read a `data-*` value off the root element. */
  option(name, fallback = null) {
    const value = this.el.dataset[name];
    return value === undefined ? fallback : value;
  }

  /** Publish on the shared bus, if one was provided. */
  publish(channel, payload) {
    this.bus?.emit(channel, payload);
  }

  /** Subscribe on the shared bus; unsubscribed on destroy(). */
  subscribe(channel, handler) {
    if (!this.bus) return () => {};
    const off = this.bus.on(channel, handler.bind(this));
    this._bindings.push({
      target: { removeEventListener: off },
      type: channel,
      handler,
      options: undefined,
    });
    return off;
  }
}
