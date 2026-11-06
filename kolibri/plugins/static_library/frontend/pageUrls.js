import cloneDeepWith from 'lodash/cloneDeepWith';
import urls from 'kolibri/urls';

// Kolibri's URL settings for the export's files, which it resolves against the
// page's origin, rather than the page
const URL_SETTINGS = ['__staticUrl', '__contentUrl', '__zipContentUrl', '__sandboxUrl'];

const domParser = new DOMParser();

// As kolibri-plugin-data and Kolibri's content viewers read a template's JSON
function readTemplate(template) {
  const text = domParser.parseFromString(template.innerHTML.trim(), 'text/html').documentElement
    .textContent;
  return JSON.parse(text);
}

function writeTemplate(template, data) {
  // Escaped, as Django writes it marked safe
  template.innerHTML = JSON.stringify(data)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * The export writes the page's URLs of its files relative to the page, so the
 * library can be served from any path, as a GitHub Pages project site. This
 * resolves them against the page where Kolibri needs them whole: in its URL
 * settings, and in content viewers' and other plugins' data, which they can use
 * from the frames content plays in. Their plugins read that data once they load,
 * after this page's.
 * @param {string[]} relativeRoots - The folders of the export's files, relative to
 * the page
 * @returns {function((string|undefined)): (string|undefined)} Resolves a URL under
 * those folders against the page, and leaves anything else as it is
 */
export default function resolvePageUrls(relativeRoots) {
  const page = new URL('.', document.baseURI).href;

  function resolve(value) {
    return typeof value === 'string' && relativeRoots.some(root => value.startsWith(root))
      ? new URL(value, page).href
      : value;
  }

  Object.defineProperties(
    urls,
    Object.fromEntries(URL_SETTINGS.map(key => [key, { value: resolve(urls[key]) }])),
  );
  for (const template of document.querySelectorAll(
    'template[data-viewer], template[data-plugin]',
  )) {
    const data = cloneDeepWith(readTemplate(template), value =>
      typeof value === 'string' ? resolve(value) : undefined,
    );
    writeTemplate(template, data);
  }
  return resolve;
}
