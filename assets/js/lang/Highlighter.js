import { uqulangGrammar, shellGrammar, jsonGrammar, textGrammar } from './grammars.js';

/**
 * Tiny, dependency-free syntax highlighter.
 *
 * It is purely additive: a `<pre><code>` block is already readable plain text,
 * and highlighting only replaces that text with the same characters wrapped in
 * `<span class="tok-*">`. If this module fails to load, the code still reads.
 *
 * Input is escaped before any markup is produced, so a sample containing
 * `<script>` is displayed, never executed.
 */
export class Highlighter {
  constructor() {
    /** @type {Map<string, import('./grammars.js').Grammar>} */
    this.grammars = new Map();

    this.register('uqulang', uqulangGrammar);
    this.register('uqu', uqulangGrammar);
    this.register('shell', shellGrammar);
    this.register('bash', shellGrammar);
    this.register('console', shellGrammar);
    this.register('json', jsonGrammar);
    this.register('text', textGrammar);
  }

  register(name, grammar) {
    this.grammars.set(name.toLowerCase(), grammar);
    return this;
  }

  static escape(value) {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  /**
   * @param {string} source raw code
   * @param {string} language grammar name
   * @returns {string} HTML
   */
  highlight(source, language) {
    const grammar = this.grammars.get(String(language || '').toLowerCase());
    if (!grammar || grammar.rules.length === 0) return Highlighter.escape(source);

    let html = '';
    for (const { type, value } of grammar.tokenize(source)) {
      const escaped = Highlighter.escape(value);
      html += type ? `<span class="tok-${type}">${escaped}</span>` : escaped;
    }
    return html;
  }
}

/** One shared instance is enough for a page. */
export const highlighter = new Highlighter();
