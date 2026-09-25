import { Component } from '../core/Component.js';

/**
 * Mobile navigation drawer.
 *
 * Keyboard and screen-reader behaviour is the point of this component:
 * Escape closes, focus is kept inside while open, and the toggle button
 * carries `aria-expanded` / `aria-controls`.
 */
export class NavDrawer extends Component {
  static selector = '[data-nav-drawer]';
  static BREAKPOINT = '(max-width: 60rem)';

  mount() {
    this.toggle = this.$('[data-nav-toggle]');
    this.panel = this.$('[data-nav-panel]');
    if (!this.toggle || !this.panel) return;

    this.media = window.matchMedia(NavDrawer.BREAKPOINT);

    this.toggle.setAttribute('aria-expanded', 'false');
    this.toggle.setAttribute('aria-controls', this.panel.id || 'site-nav');
    if (!this.panel.id) this.panel.id = 'site-nav';

    this._applyViewport();

    this.on(this.toggle, 'click', this._onToggle);
    this.on(this.media, 'change', this._applyViewport);
    this.on(document, 'keydown', this._onKeydown);
    this.on(document, 'click', this._onDocumentClick);
    this.on(this.panel, 'keydown', this._onPanelKeydown);
  }

  get isOpen() { return this.toggle?.getAttribute('aria-expanded') === 'true'; }

  open() {
    this.panel.hidden = false;
    this.toggle.setAttribute('aria-expanded', 'true');
    this.panel.querySelector('a, button')?.focus();
  }

  close({ restoreFocus = false } = {}) {
    if (!this.media.matches) return;
    this.panel.hidden = true;
    this.toggle.setAttribute('aria-expanded', 'false');
    if (restoreFocus) this.toggle.focus();
  }

  _onToggle(event) {
    event.preventDefault();
    this.isOpen ? this.close({ restoreFocus: true }) : this.open();
  }

  /** Narrow viewport: drawer starts closed. Wide viewport: always visible. */
  _applyViewport() {
    if (this.media.matches) {
      this.panel.hidden = true;
      this.toggle.setAttribute('aria-expanded', 'false');
    } else {
      this.panel.hidden = false;
      this.toggle.setAttribute('aria-expanded', 'false');
    }
  }

  _onKeydown(event) {
    if (event.key === 'Escape' && this.isOpen) {
      this.close({ restoreFocus: true });
    }
  }

  _onDocumentClick(event) {
    if (!this.isOpen) return;
    if (this.el.contains(event.target)) return;
    this.close();
  }

  /** Simple focus loop so Tab cannot escape the open drawer. */
  _onPanelKeydown(event) {
    if (event.key !== 'Tab' || !this.isOpen) return;

    const focusable = Array.from(
      this.panel.querySelectorAll('a[href], button:not([disabled]), input, [tabindex]:not([tabindex="-1"])')
    ).filter((node) => node.offsetParent !== null);

    if (focusable.length === 0) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      this.toggle.focus();
    }
  }
}
