import cloneDeep from 'lodash/cloneDeep';

const ID = /^[0-9a-f]{32}$/;

/**
 * The library's JSON files, written beside the page by the exportstaticlibrary
 * command (see the plugin's export.py for what each one holds). Files are fetched
 * once, and each caller gets its own copy to change.
 * @param {string} dataUrl - Where the files are.
 * @returns {object} Loaders for each kind of file
 */
export default function createLibrary(dataUrl) {
  const files = new Map();
  // The export writes the files' URLs relative to the library's data, so it works
  // wherever it is served from; requests made elsewhere, as from the frames content
  // plays in, need them whole
  const base = new URL(dataUrl, document.baseURI);

  function whole(url) {
    return url ? new URL(url, base).href : url;
  }

  function withWholeUrls(node) {
    if (!node) {
      return node;
    }
    if ('thumbnail' in node) {
      node.thumbnail = whole(node.thumbnail);
    }
    for (const file of node.files || []) {
      file.storage_url = whole(file.storage_url);
    }
    return node;
  }

  function load(path) {
    if (!files.has(path)) {
      // These files are this page's server: there is no API to ask through
      const loading = fetch(dataUrl + path).then(response => {
        if (response.ok) {
          return response.json();
        }
        if (response.status === 404) {
          return null;
        }
        throw new Error(`Could not load ${path}: ${response.status} ${response.statusText}`);
      });
      // Try again next time, rather than keep a failure
      loading.catch(() => files.delete(path));
      files.set(path, loading);
    }
    return files.get(path).then(cloneDeep);
  }

  function loadById(folder, id) {
    return ID.test(id) ? load(`${folder}/${id}.json`) : Promise.resolve(null);
  }

  async function indexRows(channelId) {
    const index = await loadById('index', channelId);
    if (!index) {
      return [];
    }
    return index.rows.map(row => {
      const node = { channel_id: channelId };
      index.fields.forEach((field, i) => {
        node[field] = row[i];
      });
      return node;
    });
  }

  return {
    summary: () => load('library.json'),
    channels: async () =>
      (await load('channels.json')).map(channel => ({
        ...channel,
        thumbnail: whole(channel.thumbnail),
      })),
    node: async id => withWholeUrls(await loadById('nodes', id)),
    children: async id => ((await loadById('children', id)) || []).map(withWholeUrls),
    async nodes(ids) {
      const nodes = await Promise.all(ids.map(id => loadById('nodes', id)));
      return nodes.filter(Boolean).map(withWholeUrls);
    },
    async indexRows(channelIds) {
      return (await Promise.all(channelIds.map(indexRows))).flat();
    },
  };
}
