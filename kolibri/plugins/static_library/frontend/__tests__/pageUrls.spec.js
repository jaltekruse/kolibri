import urls from 'kolibri/urls';
import resolvePageUrls from '../pageUrls';

jest.mock('kolibri/urls', () => ({
  __esModule: true,
  // As the export writes them, relative to the page
  default: {
    __staticUrl: 'static/',
    __contentUrl: 'content/storage/',
    __zipContentUrl: 'content/zipcontent/',
    __sandboxUrl: 'content/static/sandbox/sandbox-1.html',
  },
}));

// Served from a path, as a GitHub Pages project site
const PAGE = 'https://example.github.io/library/';
const RELATIVE_ROOTS = ['content/', 'library/', 'static/'];

function addTemplate(attribute, name, data) {
  const template = document.createElement('template');
  template.setAttribute(attribute, name);
  template.innerHTML = JSON.stringify(data);
  document.body.appendChild(template);
  return template;
}

// As kolibri-plugin-data and Kolibri's content viewers read a template
function read(template) {
  const text = new DOMParser().parseFromString(template.innerHTML.trim(), 'text/html')
    .documentElement.textContent;
  return JSON.parse(text);
}

describe('resolvePageUrls', () => {
  let viewer;
  let plugin;
  let resolve;

  beforeAll(() => {
    const base = document.createElement('base');
    base.href = `${PAGE}index.html`;
    document.head.appendChild(base);
    viewer = addTemplate('data-viewer', 'kolibri.plugins.html5_viewer.main', {
      urls: ['static/html5_viewer.js'],
      presets: ['html5_zip'],
      sandboxHandlerUrl: 'content/static/html5_viewer.sandbox_handler.js',
    });
    plugin = addTemplate('data-plugin', 'kolibri.plugins.media_player.main', {
      youtubePlayerUrl: 'content/static/youtube/player.html',
      note: 'Tom & Jerry <3',
    });
    resolve = resolvePageUrls(RELATIVE_ROOTS);
  });

  it("resolves Kolibri's URL settings against the page", () => {
    expect(urls.__staticUrl).toBe(`${PAGE}static/`);
    expect(urls.__zipContentUrl).toBe(`${PAGE}content/zipcontent/`);
    expect(urls.__sandboxUrl).toBe(`${PAGE}content/static/sandbox/sandbox-1.html`);
  });

  it("resolves the URLs in content viewers' and plugins' data against the page", () => {
    expect(read(viewer)).toEqual({
      urls: [`${PAGE}static/html5_viewer.js`],
      presets: ['html5_zip'],
      sandboxHandlerUrl: `${PAGE}content/static/html5_viewer.sandbox_handler.js`,
    });
    expect(read(plugin)).toEqual({
      youtubePlayerUrl: `${PAGE}content/static/youtube/player.html`,
      note: 'Tom & Jerry <3',
    });
  });

  it("resolves the export's URLs it is given, and leaves other strings alone", () => {
    expect(resolve('library/')).toBe(`${PAGE}library/`);
    expect(resolve('html5_zip')).toBe('html5_zip');
  });
});
