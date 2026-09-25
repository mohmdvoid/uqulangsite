/* Inlined into every page's <head>. Kept here as the canonical copy.
   Runs before first paint: swaps the no-js class and applies the stored theme
   so there is no flash of the wrong colour scheme. */
(function () {
  var root = document.documentElement;
  root.classList.remove('no-js');
  root.classList.add('js');
  try {
    var theme = window.localStorage.getItem('uqulang:theme');
    if (theme === 'dark' || theme === 'light') root.setAttribute('data-theme', theme);
  } catch (e) {
    /* storage blocked: fall back to the OS preference */
  }
})();
