/*
 * An axios adapter that answers Kolibri's API requests from the library's files, for
 * a page with no Kolibri server behind it. It answers what Learn's pages ask for a
 * guest: browsing and searching channels, and starting and updating sessions with
 * resources. Anything else is a 404.
 */

import escapeRegExp from 'lodash/escapeRegExp';
import logger from 'kolibri-logging';
import urls from 'kolibri/urls';
import {
  availableLabels,
  hasFilters,
  indexRow,
  inTreeOrder,
  nodeFilter,
  page,
  queryParams,
  tree,
} from './contentQueries';
import createLibrary from './library';
import createProgressTracking, { ProgressTrackingError } from './progressTracking';

const logging = logger.getLogger(__filename);

const ID_PLACEHOLDER = '__id__';

// What Kolibri tells a guest about the facility they would sign in to. A static
// library has no facility, so nothing here lets a guest do more than browse.
const FACILITY_ID = '0'.repeat(32);
const FACILITY_DATASET = {
  id: FACILITY_ID,
  description: '',
  location: '',
  preset: 'formal',
  allow_guest_access: true,
  learner_can_sign_up: false,
  learner_can_login_with_no_password: false,
  learner_can_edit_username: false,
  learner_can_edit_name: false,
  learner_can_edit_password: false,
  learner_can_delete_account: false,
  show_download_button_in_learn: false,
  enable_mark_attendance: false,
  picture_password_settings: null,
  registered: false,
  is_full_facility_import: true,
  extra_fields: { facility: {}, on_my_own_setup: false, pin_code: '' },
};
const FACILITY = {
  id: FACILITY_ID,
  name: '',
  num_users: 0,
  num_classrooms: 0,
  num_learners: 0,
  last_successful_sync: null,
  last_failed_sync: null,
  picture_passwords_exhausted: false,
  dataset: FACILITY_DATASET,
};

class NotFound extends Error {}

function anonymousSession() {
  return {
    username: '',
    full_name: '',
    user_id: null,
    facility_id: FACILITY_ID,
    kind: ['anonymous'],
    full_facility_import: true,
    id: 'current',
    server_time: new Date().toISOString(),
    app_context: false,
  };
}

/**
 * A pattern matching the paths of one of Kolibri's URLs, capturing its id, or null
 * when this Kolibri has no such URL.
 * @param {string} name - Its name in Kolibri's URL patterns, as kolibri:core:session_detail
 * @param {boolean} [withId] - Whether the URL takes an id
 * @returns {RegExp|null}
 */
function urlPattern(name, withId = false) {
  const urlFunction = urls[name];
  if (!urlFunction) {
    return null;
  }
  const url = withId ? urlFunction(ID_PLACEHOLDER) : urlFunction();
  return new RegExp(`^${url.split(ID_PLACEHOLDER).map(escapeRegExp).join('([^/]+)')}$`);
}

function response(config, status, data) {
  const result = { data, status, statusText: String(status), headers: {}, config, request: {} };
  if (status >= 200 && status < 300) {
    return result;
  }
  const error = new Error(`Request failed with status code ${status}`);
  Object.assign(error, { config, response: result, isAxiosError: true });
  throw error;
}

/**
 * An axios adapter answering Kolibri's API requests from the library's files.
 * @param {string} dataUrl - Where the library's files are
 * @returns {function(object): Promise<object>} An axios adapter
 */
export default function createLibraryAdapter(dataUrl) {
  const library = createLibrary(dataUrl);
  const progressTracking = createProgressTracking();

  async function context() {
    const summary = await library.summary();
    return {
      summary,
      courseIds: new Set(summary.course_ids),
      stopwords: new Set(summary.stopwords),
    };
  }

  // A test of whether an index row passes the query's filters
  async function rowFilter(query, { stopwords }) {
    const ancestor = query.descendant_of ? await library.node(query.descendant_of) : null;
    return nodeFilter(query, { stopwords, ancestor });
  }

  // A test of whether a node passes the query's filters
  async function nodeFilterFor(query, queryContext) {
    const include = await rowFilter(query, queryContext);
    return node => include(indexRow(node, queryContext.courseIds));
  }

  // The nodes a query can match, loading as few of the library's files as it can
  async function candidates(query, { summary, courseIds }) {
    const rows = nodes => nodes.map(node => indexRow(node, courseIds));
    if (query.ids) {
      return rows(await library.nodes(query.ids.split(',')));
    }
    if (query.parent) {
      return rows(await library.children(query.parent));
    }
    if (query.parent__isnull === 'true') {
      return rows(await library.nodes(summary.channels.map(channel => channel.root)));
    }
    let channelIds = summary.channels.map(channel => channel.id);
    if (query.channel_id) {
      channelIds = channelIds.filter(id => id === query.channel_id);
    }
    if (query.channels) {
      const channels = query.channels.split(',');
      channelIds = channelIds.filter(id => channels.includes(id));
    }
    if (query.tree_id) {
      const channel = summary.channels.find(c => c.tree_id === Number(query.tree_id));
      channelIds = channelIds.filter(id => channel && id === channel.id);
    }
    return library.indexRows(channelIds);
  }

  async function listNodes(query) {
    const queryContext = await context();
    const { summary } = queryContext;
    const paginated = query.max_results !== undefined;
    const end = (Number(query.cursor) || 0) + Number(query.max_results);
    if (paginated && !hasFilters(query) && end <= summary.first_nodes.length) {
      // A page of the whole library, as the library page asks for, without loading
      // every channel's index
      const { ids } = page(
        summary.first_nodes.map(id => ({ id })),
        query,
      );
      return {
        more: end < summary.count ? { ...query, cursor: String(end) } : null,
        results: await library.nodes(ids),
        labels: summary.labels,
      };
    }
    const include = await rowFilter(query, queryContext);
    const matches = inTreeOrder((await candidates(query, queryContext)).filter(include));
    if (!paginated) {
      return library.nodes(matches.map(node => node.id));
    }
    const { ids, more } = page(matches, query);
    return {
      more,
      results: await library.nodes(ids),
      labels: availableLabels(matches, summary.labels),
    };
  }

  async function nodeTree(id, query) {
    const include = await nodeFilterFor(query, await context());
    const result = await tree(id, query, {
      node: library.node,
      children: library.children,
      include,
    });
    if (!result) {
      throw new NotFound();
    }
    return result;
  }

  // ContentNodeViewset.recommendations_for: the resources beside this one
  async function recommendationsFor(id, query) {
    const include = await nodeFilterFor(query, await context());
    const node = await library.node(id);
    if (!node || !include(node)) {
      throw new NotFound();
    }
    // A channel's root has no siblings here, only other channels' roots
    const siblings = node.parent ? await library.children(node.parent) : [];
    return siblings
      .filter(sibling => sibling.id !== id && sibling.kind !== 'topic')
      .filter(include);
  }

  async function channels(query) {
    const all = await library.channels();
    return query.available === 'false' ? [] : all;
  }

  async function found(promise) {
    const result = await promise;
    if (!result) {
      throw new NotFound();
    }
    return result;
  }

  // [method, URL name, whether it takes an id, answer]
  const routes = [
    ['get', 'kolibri:core:session_detail', true, () => anonymousSession()],
    ['put', 'kolibri:core:session_detail', true, () => anonymousSession()],
    ['patch', 'kolibri:core:session_detail', true, () => anonymousSession()],
    [
      'get',
      'kolibri:kolibri.plugins.learn:state',
      false,
      () => ({ in_classes: false, can_download_externally: false }),
    ],
    ['get', 'kolibri:core:facility_list', false, () => [FACILITY]],
    ['get', 'kolibri:core:facility_detail', true, () => FACILITY],
    ['get', 'kolibri:core:facilitydataset_list', false, () => [FACILITY_DATASET]],
    ['get', 'kolibri:core:bookmarks_list', false, () => []],
    ['get', 'kolibri:core:channel_list', false, ({ query }) => channels(query)],
    [
      'get',
      'kolibri:core:channel_detail',
      true,
      ({ id }) => found(library.channels().then(all => all.find(c => c.id === id))),
    ],
    ['get', 'kolibri:core:contentnode_list', false, ({ query }) => listNodes(query)],
    ['get', 'kolibri:core:contentnode_detail', true, ({ id }) => found(library.node(id))],
    ['get', 'kolibri:core:contentnode_tree_detail', true, ({ id, query }) => nodeTree(id, query)],
    [
      'get',
      'kolibri:core:contentnode_recommendations_for',
      true,
      ({ id, query }) => recommendationsFor(id, query),
    ],
    ['post', 'kolibri:core:trackprogress_list', false, ({ data }) => progressTracking.start(data)],
    [
      'put',
      'kolibri:core:trackprogress_detail',
      true,
      ({ id, data }) => found(progressTracking.update(id, data)),
    ],
  ]
    .map(([method, name, withId, answer]) => ({
      method,
      pattern: urlPattern(name, withId),
      answer,
    }))
    .filter(route => route.pattern);

  return async function libraryAdapter(config) {
    const url = new URL(config.url, window.location.origin);
    const method = (config.method || 'get').toLowerCase();
    const query = { ...Object.fromEntries(url.searchParams), ...queryParams(config.params) };
    const data = typeof config.data === 'string' ? JSON.parse(config.data) : config.data || {};
    for (const route of routes) {
      const match = url.pathname.match(route.pattern);
      if (match && route.method === method) {
        try {
          return response(config, 200, await route.answer({ id: match[1], query, data }));
        } catch (error) {
          if (error instanceof NotFound) {
            return response(config, 404, { detail: 'Not found.' });
          }
          if (error instanceof ProgressTrackingError || error instanceof RangeError) {
            return response(config, 400, [error.message]);
          }
          throw error;
        }
      }
    }
    logging.warn(`The static library has no answer for ${method.toUpperCase()} ${url.pathname}`);
    return response(config, 404, { detail: 'Not found.' });
  };
}
