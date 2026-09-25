import { Component } from '../core/Component.js';
import { highlighter } from '../lang/Highlighter.js';

/**
 * Enhances one `<pre><code>` sample: syntax colours plus a copy button.
 *
 * The original text is captured before highlighting, so "copy" always yields
 * exactly what the author wrote — no span markup, no smart quotes. Shell
 * samples drop their leading `$ ` prompts on copy so the command can be pasted
 * straight into a terminal.
 */
export class CodeBlock extends Component {
  static selector = '[data-code]';

  mount() {
    this.codeEl = this.$('code');
    if (!this.codeEl) return;

    this.language = this.option('lang', 'text');
    this.source = this.codeEl.textContent.replace(/\n$/, '');

    this._highlight();
    this._setupCopy();
  }

  _highlight() {
    try {
      this.codeEl.innerHTML = highlighter.highlight(this.source, this.language);
    } catch (error) {
      // Leave the plain text in place: unhighlighted code is still correct code.
      console.error('[code] highlight failed', error);
    }
  }

  _setupCopy() {
    this.button = this.$('[data-code-copy]');
    if (!this.button) return;

    if (!navigator.clipboard) {
      this.button.hidden = true;
      return;
    }

    this.on(this.button, 'click', this._onCopy);
  }

  get copyText() {
    const isShell = ['shell', 'bash', 'console'].includes(this.language);
    if (!isShell) return this.source;
    return this.source
      .split('\n')
      .filter((line) => !line.trim().startsWith('#'))
      .map((line) => line.replace(/^\s*[$>]\s+/, ''))
      .join('\n')
      .trim();
  }

  async _onCopy() {
    const label = this.$('[data-code-copy-label]');
    try {
      await navigator.clipboard.writeText(this.copyText);
      this.button.dataset.state = 'copied';
      if (label) label.textContent = 'Copied';
      this.button.setAttribute('aria-live', 'polite');

      clearTimeout(this._resetTimer);
      this._resetTimer = setTimeout(() => {
        delete this.button.dataset.state;
        if (label) label.textContent = 'Copy';
      }, 2000);
    } catch (error) {
      if (label) label.textContent = 'Press Ctrl+C';
      console.error('[code] copy failed', error);
    }
  }

  destroy() {
    clearTimeout(this._resetTimer);
    super.destroy();
  }
}
