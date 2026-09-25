/**
 * Entry point. Loaded as `<script type="module" defer>`, so it never blocks
 * rendering and it is only fetched by browsers that support modules.
 *
 * Order matters in one place: TabGroup is registered before PlatformDetector so
 * that the tab groups are already listening when the detected platform is
 * announced.
 */
import { App } from './core/App.js';

import { ThemeToggle } from './components/ThemeToggle.js';
import { NavDrawer } from './components/NavDrawer.js';
import { TabGroup } from './components/TabGroup.js';
import { CodeBlock } from './components/CodeBlock.js';
import { PlatformDetector } from './components/PlatformDetector.js';
import { TableOfContents } from './components/TableOfContents.js';
import { HeadingAnchors } from './components/HeadingAnchors.js';
import { DocsSearch } from './components/DocsSearch.js';

const app = new App({ namespace: 'uqulang' })
  .register(
    ThemeToggle,
    NavDrawer,
    CodeBlock,
    TabGroup,
    PlatformDetector,
    TableOfContents,
    HeadingAnchors,
    DocsSearch
  )
  .boot();

// Exposed for debugging only; nothing on the site reads it.
window.__uqulang = app;
