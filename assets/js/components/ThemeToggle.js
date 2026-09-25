import { Component } from '../core/Component.js';

/**
 * Light / dark switch.
 *
 * The *initial* theme is applied by a tiny inline script in <head> so there is
 * no flash of the wrong colours before this module loads. This component only
 * handles the toggling afterwards, and keeps the choice in localStorage.
 *
 * Three states are possible: "light", "dark", and no stored preference at all,
 * which means "follow the operating system".
 */
export class ThemeToggle extends Component {
  static selector = '[data-theme-toggle]';
  static STORAGE_KEY = 'theme';

  mount() {
    this._media = window.matchMedia('(prefers-color-scheme: dark)');
    this._syncLabel();

    this.on(this.el, 'click', this._onClick);

    // Follow the OS while the visitor has no explicit preference.
    this.on(this._media, 'change', this._syncLabel);
  }

  _onClick() {
    const next = this._effectiveTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    this.store?.set(ThemeToggle.STORAGE_KEY, next);
    this._syncLabel();
    this.publish('theme:change', { theme: next });
  }

  _effectiveTheme() {
    const explicit = document.documentElement.getAttribute('data-theme');
    if (explicit === 'light' || explicit === 'dark') return explicit;
    return this._media.matches ? 'dark' : 'light';
  }

  _syncLabel() {
    const isDark = this._effectiveTheme() === 'dark';
    const label = isDark ? 'Switch to light theme' : 'Switch to dark theme';
    this.el.setAttribute('aria-label', label);
    this.el.setAttribute('title', label);
    this.el.setAttribute('aria-pressed', String(isDark));
  }
}
