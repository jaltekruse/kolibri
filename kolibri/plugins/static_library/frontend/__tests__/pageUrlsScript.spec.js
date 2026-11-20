// The script the export writes into the page, to run before Kolibri's scripts
const SCRIPT = '../../templates/static_library/page_urls.js';

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

function runScript() {
  const script = document.createElement('script');
  script.setAttribute('data-relative-roots', JSON.stringify(RELATIVE_ROOTS));
  document.body.appendChild(script);
  jest.isolateModules(() => require(SCRIPT));
}

describe('the page URLs script', () => {
  let viewer;
  let plugin;
  let core;

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
    core = addTemplate('data-plugin', 'kolibri.core.default_frontend', {
      fullCSSFileModern: 'static/assets/fonts/noto-full.css',
      urls: {
        prefix: '/',
        urls: { kolibri_core_example: [['static/example/', []]] },
        __staticUrl: 'static/',
        __zipContentUrl: 'content/zipcontent/',
        __sandboxUrl: 'content/static/sandbox/sandbox-1.html',
      },
    });
    runScript();
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

  it("resolves Kolibri's URL settings against the page, but not its API's URL patterns", () => {
    expect(read(core)).toEqual({
      fullCSSFileModern: `${PAGE}static/assets/fonts/noto-full.css`,
      urls: {
        prefix: '/',
        urls: { kolibri_core_example: [['static/example/', []]] },
        __staticUrl: `${PAGE}static/`,
        __zipContentUrl: `${PAGE}content/zipcontent/`,
        __sandboxUrl: `${PAGE}content/static/sandbox/sandbox-1.html`,
      },
    });
  });
});
