import { Component } from '../core/Component.js';

/**
 * Adds a permalink control to every heading that already has an id, so a
 * reader can link somebody straight to the paragraph they are talking about.
 */
export class HeadingAnchors extends Component {
  static selector = '[data-heading-anchors]';

  mount() {
    for (const heading of this.$$('h2[id], h3[id], h4[id]')) {
      if (heading.querySelector('.heading-anchor')) continue;

      const anchor = document.createElement('a');
      anchor.className = 'heading-anchor';
      anchor.href = `#${heading.id}`;
      anchor.textContent = '#';
      anchor.setAttribute('aria-label', `Link to “${heading.textContent.trim()}”`);
      heading.append(anchor);
    }
  }
}
