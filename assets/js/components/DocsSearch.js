import { Component } from '../core/Component.js';

/**
 * Client-side documentation search over a small static JSON index.
 *
 * Why not a hosted search service: this keeps the docs searchable with zero
 * third-party requests, zero API keys and zero runtime cost, and it cannot
 * break the page — if the index fails to load, the input is simply removed and
 * the sidebar remains the way to navigate.
 *
 * The index is fetched lazily on first focus, so it costs nothing to visitors
 * who never search.
 */
export class DocsSearch extends Component {
  static selector = '[data-search]';
  static MAX_RESULTS = 8;

  mount() {
    this.input = this.$('[data-search-input]');
    this.output = this.$('[data-search-results]');
    this.status = this.$('[data-search-status]');
    this.indexUrl = this.option('search');
    if (!this.input || !this.output || !this.indexUrl) return;

    this.entries = null;
    this.loading = null;
    this.activeIndex = -1;

    this.on(this.input, 'focus', this._ensureIndex, { once: true });
    this.on(this.input, 'input', this._onInput);
    this.on(this.input, 'keydown', this._onKeydown);
    this.on(document, 'click', this._onDocumentClick);
  }

  async _ensureIndex() {
    if (this.entries || this.loading) return this.loading;

    this.loading = fetch(this.indexUrl, { headers: { accept: 'application/json' } })
      .then((response) => {
        if (!response.ok) throw new Error(`index ${response.status}`);
        return response.json();
      })
      .then((data) => {
        this.entries = Array.isArray(data) ? data : data.entries ?? [];
        return this.entries;
      })
      .catch((error) => {
        console.error('[search] index unavailable', error);
        this.el.hidden = true;
        return [];
      });

    return this.loading;
  }

  async _onInput() {
    const query = this.input.value.trim();
    if (query.length < 2) {
      this._clear();
      return;
    }

    await this._ensureIndex();
    if (!this.entries) return;

    this._renderResults(DocsSearch.rank(this.entries, query).slice(0, DocsSearch.MAX_RESULTS), query);
  }

  /**
   * Scores by where the query appears: title beats section heading beats body.
   * Deliberately simple and predictable — a docs set this size does not need
   * fuzzy matching, and predictable beats clever.
   */
  static rank(entries, query) {
    const needle = query.toLowerCase();
    const terms = needle.split(/\s+/).filter(Boolean);

    return entries
      .map((entry) => {
        const title = (entry.title || '').toLowerCase();
        const section = (entry.section || '').toLowerCase();
        const body = (entry.body || '').toLowerCase();

        let score = 0;
        if (title === needle) score += 120;
        if (title.startsWith(needle)) score += 60;
        if (title.includes(needle)) score += 40;
        if (section.includes(needle)) score += 20;
        if (body.includes(needle)) score += 10;

        for (const term of terms) {
          if (title.includes(term)) score += 8;
          if (body.includes(term)) score += 2;
        }

        return { entry, score };
      })
      .filter((row) => row.score > 0)
      .sort((a, b) => b.score - a.score)
      .map((row) => row.entry);
  }

  _renderResults(results, query) {
    this.activeIndex = -1;

    if (results.length === 0) {
      this.output.innerHTML = `<li class="docs-search__empty">No matches for “${DocsSearch.escape(query)}”.</li>`;
      this._announce(`No results for ${query}`);
      return;
    }

    this.output.innerHTML = results
      .map(
        (entry) => `<li><a class="docs-search__result" href="${DocsSearch.escape(entry.url)}">
            ${DocsSearch.escape(entry.title)}
            <small>${DocsSearch.escape(entry.section || 'Documentation')}</small>
          </a></li>`
      )
      .join('');

    this.results = Array.from(this.output.querySelectorAll('.docs-search__result'));
    this._announce(`${results.length} result${results.length === 1 ? '' : 's'}`);
  }

  /** Screen readers get the result count; the list itself is plain links. */
  _announce(message) {
    if (this.status) this.status.textContent = message;
  }

  _onKeydown(event) {
    if (!this.results?.length) return;

    if (event.key === 'Escape') {
      this._clear();
      this.input.blur();
      return;
    }

    if (event.key === 'Enter' && this.activeIndex > -1) {
      event.preventDefault();
      this.results[this.activeIndex].click();
      return;
    }

    const delta = event.key === 'ArrowDown' ? 1 : event.key === 'ArrowUp' ? -1 : 0;
    if (delta === 0) return;

    event.preventDefault();
    this.activeIndex = (this.activeIndex + delta + this.results.length) % this.results.length;

    this.results.forEach((node, i) => {
      if (i === this.activeIndex) node.dataset.active = 'true';
      else delete node.dataset.active;
    });
  }

  _onDocumentClick(event) {
    if (!this.el.contains(event.target)) this._clear();
  }

  _clear() {
    this.output.innerHTML = '';
    this.results = [];
    this.activeIndex = -1;
    this._announce('');
  }

  static escape(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}
