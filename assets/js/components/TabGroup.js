import { Component } from '../core/Component.js';

/**
 * ARIA tabs with arrow-key navigation.
 *
 * Markup is authored so that *without* JavaScript every panel is visible with
 * its own heading (see `.no-js .tabs__panel` in components.css). This component
 * then hides all but one and wires up the tablist.
 *
 * A group with `data-sync="platform"` shares its selection with every other
 * group carrying the same key, and remembers it — so choosing "Linux" once on
 * the install page keeps every later snippet on Linux.
 */
export class TabGroup extends Component {
  static selector = '[data-tabs]';

  mount() {
    this.tabs = this.$$('[role="tab"]');
    this.panels = this.$$('[role="tabpanel"]');
    if (this.tabs.length === 0 || this.tabs.length !== this.panels.length) return;

    this.syncKey = this.option('sync');

    this.tabs.forEach((tab, index) => {
      this.on(tab, 'click', (event) => {
        event.preventDefault();
        this.select(index, { broadcast: true });
      });
      this.on(tab, 'keydown', (event) => this._onKeydown(event, index));
    });

    if (this.syncKey) {
      this.subscribe(`tabs:sync:${this.syncKey}`, ({ value, source }) => {
        if (source === this) return;
        this.selectByValue(value, { broadcast: false, persist: false });
      });
    }

    const initial = this._initialIndex();
    this.select(initial, { broadcast: false, focus: false });
  }

  _initialIndex() {
    const stored = this.syncKey ? this.store?.get(`tabs:${this.syncKey}`) : null;
    if (stored) {
      const index = this.tabs.findIndex((tab) => tab.dataset.value === stored);
      if (index > -1) return index;
    }

    const preselected = this.tabs.findIndex((tab) => tab.dataset.default !== undefined);
    return preselected > -1 ? preselected : 0;
  }

  selectByValue(value, options) {
    const index = this.tabs.findIndex((tab) => tab.dataset.value === value);
    if (index > -1) this.select(index, options);
  }

  /**
   * @param {number} index
   * @param {{broadcast?: boolean, focus?: boolean, persist?: boolean}} [options]
   */
  select(index, { broadcast = false, focus = false, persist = true } = {}) {
    this.tabs.forEach((tab, i) => {
      const selected = i === index;
      tab.setAttribute('aria-selected', String(selected));
      tab.setAttribute('tabindex', selected ? '0' : '-1');
      this.panels[i].hidden = !selected;
    });

    if (focus) this.tabs[index].focus();

    const value = this.tabs[index].dataset.value;
    if (this.syncKey && value) {
      if (persist) this.store?.set(`tabs:${this.syncKey}`, value);
      if (broadcast) this.publish(`tabs:sync:${this.syncKey}`, { value, source: this });
    }
  }

  _onKeydown(event, index) {
    const last = this.tabs.length - 1;
    const isRTL = getComputedStyle(this.el).direction === 'rtl';
    const forward = isRTL ? 'ArrowLeft' : 'ArrowRight';
    const back = isRTL ? 'ArrowRight' : 'ArrowLeft';

    let next = null;
    if (event.key === forward) next = index === last ? 0 : index + 1;
    else if (event.key === back) next = index === 0 ? last : index - 1;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = last;

    if (next === null) return;
    event.preventDefault();
    this.select(next, { broadcast: true, focus: true });
  }
}
