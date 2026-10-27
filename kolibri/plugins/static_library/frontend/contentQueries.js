/*
 * Kolibri's content API, answered in the browser from the library's files: the
 * filters, search, labels and pagination of contentnode/, and the nested pages of
 * contentnode_tree/. Each follows the server code it names, so that Learn's pages
 * get the answers they would get from Kolibri.
 */

import logger from 'kolibri-logging';

const logging = logger.getLogger(__filename);

const TOPIC = 'topic';

// kolibri/core/content/viewsets/contentnode/tree.py
const NUM_CHILDREN = 12;
const NUM_GRANDCHILDREN_PER_CHILD = 12;

// ContentNodeFilter's filters that check a node's labels
const LABEL_FILTERS = [
  'accessibility_labels',
  'categories',
  'grade_levels',
  'learner_needs',
  'learning_activities',
  'resource_types',
];

// Query parameters that are not filters
const NOT_FILTERS = ['max_results', 'cursor', 'baseurl', 'depth', 'next__gt'];

// ContentNodeFilter's filters a guest's pages don't use, so these don't answer
const UNSUPPORTED_FILTERS = [
  'prerequisite_for',
  'has_prerequisite',
  'related',
  'exclude_content_ids',
  'contains_quiz',
  'authors',
  'tags',
  'no_available_filtering',
];

const SEARCH_PARAMS = ['search', 'question', 'keywords'];

/**
 * Query parameters as the server reads them: strings, with lists comma separated,
 * as Kolibri's client sends them.
 * @param {object} params - axios params
 * @returns {object}
 */
export function queryParams(params = {}) {
  const query = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      query[key] = Array.isArray(value) ? value.join(',') : String(value);
    }
  }
  return query;
}

// django-filter's BooleanFilter
function parseBoolean(value) {
  if (['true', 'True', '1'].includes(value)) {
    return true;
  }
  if (['false', 'False', '0'].includes(value)) {
    return false;
  }
  return null;
}

function list(value) {
  return value.split(',').filter(Boolean);
}

/**
 * Search terms, as ContentNodeSearchFilter.get_search_terms splits them: by spaces
 * and punctuation, keeping quoted phrases whole, and dropping stopwords unless only
 * stopwords are left.
 * @param {string} value - What to search for
 * @param {Set<string>} stopwords - Words to leave out
 * @returns {string[]} The terms each node must match
 */
export function searchTerms(value, stopwords) {
  const terms = [];
  for (const token of value.match(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\S+/g) || []) {
    const term = token.replace(/^,+|,+$/g, '');
    if (
      term.length > 1 &&
      (term[0] === '"' || term[0] === "'") &&
      term[0] === term[term.length - 1]
    ) {
      terms.push(term.slice(1, -1).replace(/\\(.)/g, '$1'));
    } else {
      for (const subTerm of term.split(/[?.,!;:]/)) {
        if (subTerm) {
          terms.push(subTerm.trim());
        }
      }
    }
  }
  const critical = terms.filter(term => !stopwords.has(term));
  return critical.length ? critical : terms;
}

/**
 * A node's fields that filters check, as the library's index holds them.
 * @param {object} node - A node, as contentnode/<id>/ returns it
 * @param {Set<string>} courseIds - The library's courses
 * @returns {object}
 */
export function indexRow(node, courseIds) {
  return {
    ...node,
    lang_id: node.lang ? node.lang.id : null,
    in_course: node.ancestors.some(ancestor => courseIds.has(ancestor.id)),
  };
}

/**
 * Whether the query has any filter, which a page of the whole library doesn't.
 * @param {object} query - See queryParams
 * @returns {boolean}
 */
export function hasFilters(query) {
  return Object.keys(query).some(key => !NOT_FILTERS.includes(key));
}

/**
 * A test of whether a node passes the query's filters, as ContentNodeFilter and
 * ContentNodeSearchFilter apply them.
 * @param {object} query - See queryParams
 * @param {object} options - What the filters need beyond the query
 * @param {Set<string>} options.stopwords - Words search ignores
 * @param {object} [options.ancestor] - The node descendant_of names, null when there
 * is none
 * @returns {function(object): boolean} Takes an index row (see indexRow)
 */
export function nodeFilter(query, { stopwords, ancestor }) {
  const tests = [];
  const add = test => tests.push(test);
  const boolean = key => (key in query ? parseBoolean(query[key]) : null);

  for (const key of Object.keys(query)) {
    if (UNSUPPORTED_FILTERS.includes(key)) {
      logging.warn(`The static library ignores the ${key} filter`);
    }
  }
  if (query.ids) {
    const ids = new Set(list(query.ids));
    add(node => ids.has(node.id));
  }
  if (query.kind) {
    add(node => (query.kind === 'content' ? node.kind !== TOPIC : node.kind === query.kind));
  }
  if (query.kind_in) {
    const kinds = list(query.kind_in);
    add(node => kinds.includes(node.kind));
  }
  for (const field of ['parent', 'content_id', 'channel_id', 'modality']) {
    if (query[field]) {
      add(node => node[field] === query[field]);
    }
  }
  if (boolean('parent__isnull') !== null) {
    const isNull = boolean('parent__isnull');
    add(node => (node.parent === null) === isNull);
  }
  if (boolean('include_coach_content') === false) {
    add(node => !node.coach_content);
  }
  if (query.exclude_modalities) {
    const modalities = list(query.exclude_modalities);
    add(node => !modalities.includes(node.modality));
  }
  if (boolean('exclude_course_ancestry')) {
    add(node => !node.in_course);
  }
  if (query.channels) {
    const channels = list(query.channels);
    add(node => channels.includes(node.channel_id));
  }
  if (query.languages) {
    const languages = list(query.languages);
    add(node => languages.includes(node.lang_id));
  }
  if (query.tree_id) {
    add(node => node.tree_id === Number(query.tree_id));
  }
  if (query.lft__gt) {
    add(node => node.lft > Number(query.lft__gt));
  }
  if (query.rght__lt) {
    add(node => node.rght < Number(query.rght__lt));
  }
  if (query.descendant_of) {
    add(
      node =>
        Boolean(ancestor) &&
        node.tree_id === ancestor.tree_id &&
        node.lft > ancestor.lft &&
        node.rght < ancestor.rght,
    );
  }
  for (const field of LABEL_FILTERS) {
    if (query[field]) {
      const labels = list(query[field]);
      add(node => labels.every(label => (node[field] || []).includes(label)));
    }
  }
  const search = SEARCH_PARAMS.map(key => query[key]).find(value => value !== undefined);
  if (search) {
    const terms = searchTerms(search, stopwords).map(term => term.toLowerCase());
    if (terms.length) {
      add(node => {
        const title = (node.title || '').toLowerCase();
        const description = (node.description || '').toLowerCase();
        return terms.every(term => title.includes(term) || description.includes(term));
      });
    }
  }
  return node => tests.every(test => test(node));
}

/**
 * Nodes in the order Kolibri pages them, lft then id.
 * @param {object[]} nodes - Nodes or index rows
 * @returns {object[]} The nodes, sorted
 */
export function inTreeOrder(nodes) {
  return [...nodes].sort((a, b) => a.lft - b.lft || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

/**
 * The labels the nodes have, in the order the library lists them, as
 * get_available_metadata_labels gives them.
 * @param {object[]} nodes - Index rows
 * @param {object} libraryLabels - The labels of the whole library
 * @returns {object}
 */
export function availableLabels(nodes, libraryLabels) {
  const labels = {};
  for (const [field, values] of Object.entries(libraryLabels)) {
    if (field === 'languages') {
      const languages = new Set(nodes.map(node => node.lang_id));
      labels.languages = values.filter(language => languages.has(language.id));
    } else {
      const present = new Set(nodes.flatMap(node => node[field] || []));
      labels[field] = values.filter(label => present.has(label));
    }
  }
  return labels;
}

/**
 * The page of ids the query asks for, and the query for the next page, as
 * OptionalContentNodePagination pages them.
 * @param {object[]} nodes - In tree order
 * @param {object} query - See queryParams, with max_results
 * @returns {{ ids: string[], more: (object|null) }}
 */
export function page(nodes, query) {
  const offset = Number(query.cursor) || 0;
  const size = Number(query.max_results);
  const end = offset + size;
  return {
    ids: nodes.slice(offset, end).map(node => node.id),
    more: end < nodes.length ? { ...query, cursor: String(end) } : null,
  };
}

/**
 * A node with a page of its children, and of theirs, as ContentNodeTreeViewset
 * returns it.
 * @param {string} id - The node
 * @param {object} query - See queryParams: depth and next__gt, and filters
 * @param {object} options - Where nodes come from, and which pass the filters
 * @param {function(string): Promise<object>} options.node - Loads a node
 * @param {function(string): Promise<object[]>} options.children - Loads a node's
 * children, in tree order
 * @param {function(object): boolean} options.include - Whether a node passes the
 * query's filters
 * @returns {Promise<object|null>} null when there is no such node
 */
export async function tree(id, query, { node, children, include }) {
  const depth = query.depth === undefined ? 2 : Number(query.depth);
  const nextGt = query.next__gt === undefined ? null : Number(query.next__gt);
  if (![1, 2].includes(depth) || (nextGt !== null && !(nextGt >= 1))) {
    throw new RangeError('depth must be 1 or 2, and next__gt a positive integer');
  }
  const parent = await node(id);
  if (!parent || !include(parent)) {
    return null;
  }

  const includedChildren = async parentId => (await children(parentId)).filter(include);
  const firstChildren = async (parentId, after) =>
    (await includedChildren(parentId))
      .filter(child => after === null || child.lft > after)
      .slice(0, NUM_CHILDREN);

  // TreeQueryMixin.get_tree_queryset: a chain of only children is followed down
  let childNodes = await firstChildren(id, nextGt);
  const ancestors = [];
  while (nextGt === null && childNodes.length === 1) {
    ancestors.push(childNodes[0]);
    childNodes = await firstChildren(childNodes[0].id, null);
  }

  // TreeQueryMixin.get_grandchild_ids
  async function grandchildren(nodes) {
    let found = [];
    const singletons = [];
    for (const child of nodes) {
      const grandchildNodes = await includedChildren(child.id);
      if (grandchildNodes.length === 1) {
        singletons.push(grandchildNodes[0]);
      }
      found = found.concat(grandchildNodes.slice(0, NUM_GRANDCHILDREN_PER_CHILD));
    }
    if (singletons.length) {
      found = found.concat(await grandchildren(singletons));
    }
    return found;
  }
  const grandchildNodes = depth === 2 ? await grandchildren(childNodes) : [];

  // BaseContentNodeTreeViewset.retrieve: nest the nodes, in lft order
  const descendants = new Map();
  const unique = new Map(
    [...ancestors, ...childNodes, ...grandchildNodes].map(desc => [desc.id, desc]),
  );
  for (const desc of [...unique.values()].sort((a, b) => a.lft - b.lft)) {
    descendants.set(desc.id, desc);
    let descParent;
    let moreDepth;
    let pageSize;
    if (desc.parent === id) {
      descParent = parent;
      moreDepth = 2;
      pageSize = NUM_CHILDREN;
    } else if (descendants.has(desc.parent)) {
      descParent = descendants.get(desc.parent);
      moreDepth = 1;
      pageSize = NUM_GRANDCHILDREN_PER_CHILD;
    } else {
      continue;
    }
    if (!descParent.children) {
      descParent.children = { results: [], more: null };
    }
    descParent.children.results.push(desc);
    if (descParent.children.results.length === pageSize && desc.rght + 1 < descParent.rght) {
      descParent.children.more = {
        id: descParent.id,
        params: { ...query, next__gt: desc.rght, depth: moreDepth },
      };
    }
  }
  return parent;
}
