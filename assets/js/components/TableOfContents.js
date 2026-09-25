import { Component } from '../core/Component.js';

/**
 * Builds the "on this page" list from the article's own headings and highlights
 * the section currently in view.
 *
 * Generated rather than hand-maintained: a heading can never be missing from
 * the list, and the list can never point at a heading that was renamed.
 */
export class TableOfContents extends Component {
  static selector = '[data-toc]';

  mount() {
    const targetSelector = this.option('toc') || '.docs-article';
    this.article = document.querySelector(targetSelector);
    this.list = this.$('[data-toc-list]');
    if (!this.article || !this.list) return;

    this.headings = Array.from(this.article.querySelectorAll('h2[id], h3[id]'));
    if (this.headings.length < 2) {
      this.el.hidden = true;
      return;
    }

    this._render();
    this._observe();
  }

  _render() {
    const fragment = document.createDocumentFragment();

    for (const heading of this.headings) {
      const item = document.createElement('li');
      const link = document.createElement('a');

      link.className = 'docs-toc__link';
      link.href = `#${heading.id}`;
      link.dataset.depth = heading.tagName === 'H3' ? '3' : '2';
      link.textContent = heading.dataset.tocTitle || heading.textContent.trim();

      item.append(link);
      fragment.append(item);
    }

    this.list.replaceChildren(fragment);
    this.links = new Map(
      Array.from(this.list.querySelectorAll('a')).map((a) => [a.hash.slice(1), a])
    );
  }

  _observe() {
    if (!('IntersectionObserver' in window)) return;

    const offset = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--header-h'), 10) || 60;

    this.observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) this._setActive(entry.target.id);
        }
      },
      { rootMargin: `-${offset + 8}px 0px -70% 0px`, threshold: 0 }
    );

    for (const heading of this.headings) this.observer.observe(heading);
  }

  _setActive(id) {
    for (const [key, link] of this.links) {
      if (key === id) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    }
  }

  destroy() {
    this.observer?.disconnect();
    super.destroy();
  }
}
