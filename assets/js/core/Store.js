/**
 * Namespaced wrapper around localStorage.
 *
 * Storage can be unavailable or throw: private windows, blocked site data,
 * quota errors, sandboxed iframes. Every access here is guarded, and the site
 * must remain fully usable when this store silently does nothing.
 */
export class Store {
  /** @param {string} namespace */
  constructor(namespace) {
    this.namespace = namespace;
    this.available = Store.probe();
  }

  static probe() {
    try {
      const key = '__uqulang_probe__';
      window.localStorage.setItem(key, '1');
      window.localStorage.removeItem(key);
      return true;
    } catch {
      return false;
    }
  }

  _key(key) { return `${this.namespace}:${key}`; }

  get(key, fallback = null) {
    if (!this.available) return fallback;
    try {
      const raw = window.localStorage.getItem(this._key(key));
      return raw === null ? fallback : raw;
    } catch {
      return fallback;
    }
  }

  set(key, value) {
    if (!this.available) return false;
    try {
      window.localStorage.setItem(this._key(key), String(value));
      return true;
    } catch {
      return false;
    }
  }

  remove(key) {
    if (!this.available) return;
    try {
      window.localStorage.removeItem(this._key(key));
    } catch {
      /* ignore */
    }
  }
}
