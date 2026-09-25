import { EventBus } from './EventBus.js';
import { Store } from './Store.js';

/**
 * Boots the page's components.
 *
 * The single rule that matters at scale: **one broken component must never
 * take the page down.** Every construction and every mount is isolated, so a
 * failure degrades that one widget and leaves the rest of the site working.
 */
export class App {
  constructor({ namespace = 'uqulang', root = document } = {}) {
    this.root = root;
    this.bus = new EventBus();
    this.store = new Store(namespace);

    /** @type {Array<typeof import('./Component.js').Component>} */
    this.registry = [];
    /** @type {Array<import('./Component.js').Component>} */
    this.instances = [];
    /** @type {Array<{component: string, error: Error}>} */
    this.failures = [];
  }

  /** Register one or more component classes. Chainable. */
  register(...componentClasses) {
    for (const ComponentClass of componentClasses) {
      if (!ComponentClass?.selector) {
        console.warn('[app] ignoring component without a static selector', ComponentClass);
        continue;
      }
      this.registry.push(ComponentClass);
    }
    return this;
  }

  /** Find and mount everything. Safe to call once per page. */
  boot() {
    const context = { bus: this.bus, store: this.store };

    for (const ComponentClass of this.registry) {
      let elements = [];
      try {
        elements = Array.from(this.root.querySelectorAll(ComponentClass.selector));
      } catch (error) {
        this._fail(ComponentClass.name, error);
        continue;
      }

      for (const element of elements) {
        try {
          const instance = new ComponentClass(element, context);
          instance.mount();
          instance.mounted = true;
          this.instances.push(instance);
        } catch (error) {
          this._fail(ComponentClass.name, error);
        }
      }
    }

    this.bus.emit('app:ready', { instances: this.instances.length });
    return this;
  }

  destroy() {
    for (const instance of this.instances) {
      try {
        instance.destroy();
      } catch (error) {
        this._fail(instance.constructor.name, error);
      }
    }
    this.instances.length = 0;
  }

  _fail(name, error) {
    this.failures.push({ component: name, error });
    console.error(`[app] ${name} failed to mount`, error);
  }
}
