/*
 * The export writes the page's URLs of its files relative to the page, so the
 * library can be served from any path, as a GitHub Pages project site. Kolibri needs
 * some of them whole, as content viewers load files from the frames content plays
 * in, so this resolves them against the page in the data Kolibri and its plugins read,
 * before they read it: it runs before Kolibri's scripts, whichever loads first.
 */
(function () {
  var script = document.querySelector('script[data-relative-roots]');
  var roots = JSON.parse(script.getAttribute('data-relative-roots'));
  var page = new URL('.', document.baseURI).href;
  var parser = new DOMParser();

  function resolve(value) {
    for (var i = 0; i < roots.length; i++) {
      if (value.indexOf(roots[i]) === 0) {
        return new URL(value, page).href;
      }
    }
    return value;
  }

  function resolveAll(value, key, parentKey) {
    if (typeof value === 'string') {
      return resolve(value);
    }
    // The patterns of Kolibri's API URLs, which the page answers itself
    if (key === 'urls' && parentKey === 'urls') {
      return value;
    }
    if (Array.isArray(value)) {
      return value.map(function (item) {
        return resolveAll(item, null, key);
      });
    }
    if (value && typeof value === 'object') {
      var resolved = {};
      Object.keys(value).forEach(function (name) {
        resolved[name] = resolveAll(value[name], name, key);
      });
      return resolved;
    }
    return value;
  }

  // As Kolibri reads and writes this data: JSON, escaped as Django marks it safe
  function read(template) {
    return JSON.parse(
      parser.parseFromString(template.innerHTML.trim(), 'text/html').documentElement.textContent,
    );
  }

  function write(template, data) {
    template.innerHTML = JSON.stringify(data)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  var templates = document.querySelectorAll('template[data-viewer], template[data-plugin]');
  for (var i = 0; i < templates.length; i++) {
    write(templates[i], resolveAll(read(templates[i]), null, null));
  }
})();
