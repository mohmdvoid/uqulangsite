import { Component } from '../core/Component.js';

/**
 * Guesses the visitor's operating system and preselects the matching install
 * instructions, so the first thing on screen is the command they can actually
 * run.
 *
 * A guess is never sticky: an explicit choice stored by TabGroup always wins,
 * and every platform stays one click away.
 */
export class PlatformDetector extends Component {
  static selector = '[data-platform-detect]';

  static LABELS = {
    macos: 'macOS',
    linux: 'Linux',
    windows: 'Windows',
  };

  mount() {
    const stored = this.store?.get('tabs:platform');
    this.platform = stored || PlatformDetector.detect();

    if (!this.platform) return;

    for (const node of this.$$('[data-platform-label]')) {
      node.textContent = PlatformDetector.LABELS[this.platform] ?? 'your platform';
    }

    // Let already-mounted tab groups know; TabGroup ignores unknown values.
    if (!stored) {
      this.publish('tabs:sync:platform', { value: this.platform, source: this });
    }
  }

  /** @returns {'macos'|'linux'|'windows'|null} */
  static detect() {
    const hint = navigator.userAgentData?.platform || navigator.platform || '';
    const ua = navigator.userAgent || '';
    const haystack = `${hint} ${ua}`.toLowerCase();

    if (/mac|darwin|iphone|ipad/.test(haystack)) return 'macos';
    if (/win/.test(haystack)) return 'windows';
    if (/linux|x11|android|bsd/.test(haystack)) return 'linux';
    return null;
  }
}
