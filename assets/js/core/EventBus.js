/**
 * Minimal publish/subscribe channel used for cross-component messages
 * (for example: the detected platform, or a theme change).
 *
 * A subscriber that throws is isolated and reported, never allowed to break
 * the publisher or the other subscribers.
 */
export class EventBus {
  constructor({ onError } = {}) {
    /** @type {Map<string, Set<Function>>} */
    this._channels = new Map();
    this._onError = onError ?? ((error, channel) => {
      console.error(`[bus:${channel}]`, error);
    });
  }

  /**
   * @param {string} channel
   * @param {Function} handler
   * @returns {() => void} unsubscribe
   */
  on(channel, handler) {
    if (!this._channels.has(channel)) this._channels.set(channel, new Set());
    this._channels.get(channel).add(handler);
    return () => this.off(channel, handler);
  }

  off(channel, handler) {
    this._channels.get(channel)?.delete(handler);
  }

  emit(channel, payload) {
    const handlers = this._channels.get(channel);
    if (!handlers) return;

    for (const handler of Array.from(handlers)) {
      try {
        handler(payload);
      } catch (error) {
        this._onError(error, channel);
      }
    }
  }
}
