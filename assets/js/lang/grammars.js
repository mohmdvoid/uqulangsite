/**
 * Syntax grammars for the code samples on this site.
 *
 * `uqulang` keywords and builtin types live here and nowhere else — when the
 * compiler's surface syntax changes, this file is the only thing to update.
 */

/** A single lexical rule: first rule that matches at the cursor wins. */
class Rule {
  /**
   * @param {string} type  CSS token class suffix, e.g. "keyword" -> .tok-keyword
   * @param {RegExp} pattern  must be anchored-capable (used with the sticky flag)
   */
  constructor(type, pattern) {
    this.type = type;
    this.pattern = new RegExp(pattern.source, `y${pattern.flags.replace(/[gy]/g, '')}`);
  }

  matchAt(source, index) {
    this.pattern.lastIndex = index;
    const match = this.pattern.exec(source);
    return match ? match[0] : null;
  }
}

/**
 * Ordered set of rules. Tokenising is a plain left-to-right scan: linear in the
 * length of the source, no backtracking across rules, no catastrophic patterns.
 */
export class Grammar {
  /** @param {string} name @param {Array<[string, RegExp]>} rules */
  constructor(name, rules) {
    this.name = name;
    this.rules = rules.map(([type, pattern]) => new Rule(type, pattern));
  }

  /**
   * @param {string} source
   * @returns {Array<{type: string|null, value: string}>}
   */
  tokenize(source) {
    const tokens = [];
    let index = 0;
    let plain = '';

    const flushPlain = () => {
      if (plain) {
        tokens.push({ type: null, value: plain });
        plain = '';
      }
    };

    while (index < source.length) {
      let matched = null;

      for (const rule of this.rules) {
        const value = rule.matchAt(source, index);
        if (value) {
          matched = { type: rule.type, value };
          break;
        }
      }

      if (matched) {
        flushPlain();
        tokens.push(matched);
        index += matched.value.length;
      } else {
        plain += source[index];
        index += 1;
      }
    }

    flushPlain();
    return tokens;
  }
}

/* -- uqulang ------------------------------------------------------------- */

export const UQULANG_KEYWORDS = [
  'module', 'import', 'export', 'pub', 'extern',
  'func', 'return', 'let', 'var', 'const', 'static',
  'struct', 'enum', 'union', 'trait', 'impl', 'type', 'alias',
  'if', 'else', 'while', 'for', 'in', 'loop', 'match', 'case', 'default',
  'break', 'continue', 'defer', 'guard',
  'throws', 'try', 'catch', 'throw',
  'as', 'is', 'sizeof', 'alignof', 'unsafe', 'inline', 'test',
  'and', 'or', 'not', 'self', 'true', 'false', 'nil',
];

export const UQULANG_TYPES = [
  'i8', 'i16', 'i32', 'i64', 'isize',
  'u8', 'u16', 'u32', 'u64', 'usize',
  'f32', 'f64', 'bool', 'byte', 'rune', 'str', 'void', 'never',
];

const word = (list) => new RegExp(`\\b(?:${list.join('|')})\\b`);

export const uqulangGrammar = new Grammar('uqulang', [
  ['comment', /\/\/[^\n]*/],
  ['comment', /\/\*[\s\S]*?\*\//],
  ['string', /"(?:\\.|[^"\\\n])*"/],
  ['string', /'(?:\\.|[^'\\\n])*'/],
  ['attr', /@[A-Za-z_][A-Za-z0-9_]*/],
  ['keyword', word(UQULANG_KEYWORDS)],
  ['type', word(UQULANG_TYPES)],
  ['number', /\b0[xX][0-9a-fA-F_]+\b/],
  ['number', /\b0[bB][01_]+\b/],
  ['number', /\b\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?\b/],
  ['type', /\b[A-Z][A-Za-z0-9_]*\b/],
  ['func', /\b[a-z_][A-Za-z0-9_]*(?=\s*\()/],
  ['punct', /[{}()[\];,.:]|->|=>|[+\-*/%!<>=&|^~?]+/],
]);

/* -- Shell --------------------------------------------------------------- */

export const shellGrammar = new Grammar('shell', [
  ['comment', /#[^\n]*/],
  ['prompt', /^[$>](?= )/m],
  ['string', /"(?:\\.|[^"\\\n])*"/],
  ['string', /'[^'\n]*'/],
  ['attr', /(?:^|\s)--?[A-Za-z][A-Za-z0-9-]*/],
  ['keyword', /\b(?:uqu|uquc|cd|curl|tar|sudo|export|git|make|cmake|sh|brew|apt|winget|export)\b/],
  ['number', /\b\d+(?:\.\d+)*\b/],
  ['punct', /[|&;<>()]/],
]);

/* -- Plain text / other languages ---------------------------------------- */

export const textGrammar = new Grammar('text', []);

export const jsonGrammar = new Grammar('json', [
  ['comment', /\/\/[^\n]*/],
  ['attr', /"(?:\\.|[^"\\\n])*"(?=\s*:)/],
  ['string', /"(?:\\.|[^"\\\n])*"/],
  ['keyword', /\b(?:true|false|null)\b/],
  ['number', /-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b/],
  ['punct', /[{}[\],:]/],
]);
