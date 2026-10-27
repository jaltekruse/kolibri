/*
 * A library's files, as the exportstaticlibrary command writes them, for a channel
 * built from a sketch of its topics and resources.
 */

const INDEX_FIELDS = [
  'id',
  'parent',
  'content_id',
  'tree_id',
  'lft',
  'rght',
  'kind',
  'title',
  'description',
  'coach_content',
  'modality',
  'lang_id',
  'in_course',
  'accessibility_labels',
  'categories',
  'grade_levels',
  'learner_needs',
  'learning_activities',
  'resource_types',
];

export const LABELS = {
  learning_activities: ['watch', 'practice'],
  categories: [],
  grade_levels: [],
  accessibility_labels: [],
  learner_needs: [],
  resource_types: [],
  languages: [{ id: 'en', lang_name: 'English' }],
};

// A node's id, made from its name in the sketch
export function id(name) {
  return Array.from(name, char => char.charCodeAt(0).toString(16))
    .join('')
    .padEnd(32, '0');
}

function nodesOf(channelId, treeId, sketch) {
  const nodes = [];
  let position = 1;
  function visit(item, parent, ancestors) {
    const node = {
      id: id(item.name),
      content_id: id(`c${item.name}`),
      channel_id: channelId,
      parent: parent ? parent.id : null,
      ancestors,
      tree_id: treeId,
      lft: position++,
      kind: item.children ? 'topic' : item.kind || 'video',
      title: item.title || item.name,
      description: item.description || '',
      coach_content: Boolean(item.coach_content),
      modality: item.modality || null,
      lang: { id: 'en', lang_name: 'English' },
      accessibility_labels: [],
      categories: [],
      grade_levels: [],
      learner_needs: [],
      learning_activities: item.learning_activities || [],
      resource_types: [],
      files: [],
    };
    nodes.push(node);
    for (const child of item.children || []) {
      visit(child, node, [...ancestors, { id: node.id, title: node.title }]);
    }
    node.rght = position++;
  }
  visit(sketch, null, []);
  return nodes;
}

/**
 * A library's files.
 * @param {object[]} channels - Each with an id, a tree_id and the sketch of its root:
 * { name, title, kind, children, ... }
 * @returns {object} The files, by path in the library's folder
 */
export function libraryFiles(channels) {
  const files = { 'channels.json': [] };
  const all = [];
  for (const { channelId, treeId, root } of channels) {
    const nodes = nodesOf(channelId, treeId, root);
    all.push(...nodes);
    files['channels.json'].push({ id: channelId, name: root.title, root: nodes[0].id });
    for (const node of nodes) {
      files[`nodes/${node.id}.json`] = node;
      if (node.parent) {
        files[`children/${node.parent}.json`] = [
          ...(files[`children/${node.parent}.json`] || []),
          node,
        ];
      }
    }
    files[`index/${channelId}.json`] = {
      fields: INDEX_FIELDS,
      rows: nodes.map(node =>
        INDEX_FIELDS.map(field =>
          field === 'lang_id' ? node.lang.id : field === 'in_course' ? false : node[field],
        ),
      ),
    };
  }
  const ordered = [...all].sort((a, b) => a.lft - b.lft || (a.id < b.id ? -1 : 1));
  files['library.json'] = {
    channels: channels.map(({ channelId, treeId }) => ({
      id: channelId,
      root: all.find(node => node.channel_id === channelId && !node.parent).id,
      tree_id: treeId,
    })),
    count: all.length,
    first_nodes: ordered.slice(0, 25).map(node => node.id),
    labels: LABELS,
    course_ids: [],
    stopwords: ['the', 'of', 'and'],
  };
  return files;
}

/**
 * Serves the files as a static host would.
 * @param {string} dataUrl - Where the files are served from
 * @param {object} files - The files, by path
 * @returns {function(string): Promise<object>} A fetch
 */
export function staticHost(dataUrl, files) {
  return url => {
    const body = files[url.slice(dataUrl.length)];
    return Promise.resolve(
      body === undefined
        ? { ok: false, status: 404, statusText: 'Not Found' }
        : { ok: true, status: 200, json: () => Promise.resolve(JSON.parse(JSON.stringify(body))) },
    );
  };
}
