import urls from 'kolibri/urls';
import clientFactory, { setRequestAdapter } from 'kolibri/utils/baseClient';
import createLibraryAdapter from '../libraryAdapter';
import { id, LABELS, libraryFiles, staticHost } from './libraryFiles';

jest.mock('kolibri/urls');

const DATA_URL = '/library/';
const ALGEBRA = id('a1');
const GEOMETRY = id('a2');

const lessons = Array.from({ length: 13 }, (_, i) => ({
  name: `l${String(i).padStart(2, '0')}`,
  title: `Lesson ${i}`,
}));

const files = libraryFiles([
  {
    channelId: ALGEBRA,
    treeId: 1,
    root: {
      name: 'a1',
      title: 'Algebra',
      children: [
        {
          name: 'eq',
          title: 'Linear equations',
          children: [
            {
              name: 'eqv',
              title: 'Solving equations',
              description: 'Balance both sides',
              learning_activities: ['watch'],
            },
            {
              name: 'eqx',
              title: 'Practice equations',
              kind: 'exercise',
              learning_activities: ['practice'],
            },
            { name: 'eqc', title: 'Teaching equations', coach_content: true },
          ],
        },
        { name: 'ls', title: 'Lessons', children: lessons },
        {
          name: 'one',
          title: 'Only child',
          children: [{ name: 'deep', children: [{ name: 'leaf' }] }],
        },
      ],
    },
  },
  {
    channelId: GEOMETRY,
    treeId: 2,
    root: {
      name: 'a2',
      title: 'Geometry',
      children: [{ name: 'tri', title: 'Triangles and equations', learning_activities: ['watch'] }],
    },
  },
]);

let client;

async function get(name, { id: nodeId, params } = {}) {
  const url = nodeId ? urls[name](nodeId) : urls[name]();
  return (await client.get(url, { params })).data;
}

function fetchedPaths() {
  return global.fetch.mock.calls.map(([url]) => url.slice(DATA_URL.length));
}

function titles(nodes) {
  return nodes.map(node => node.title);
}

describe('libraryAdapter', () => {
  beforeEach(() => {
    urls.__echoUrls();
    global.fetch = jest.fn(staticHost(DATA_URL, files));
    client = clientFactory();
    setRequestAdapter(createLibraryAdapter(DATA_URL));
  });

  afterEach(() => {
    setRequestAdapter(null);
    delete global.fetch;
  });

  it('answers with a node as the export wrote it', async () => {
    const node = await get('kolibri:core:contentnode_detail', { id: id('eqv') });

    expect(node).toEqual(files[`nodes/${id('eqv')}.json`]);
  });

  it('answers 404 for a node the library does not have', async () => {
    await expect(get('kolibri:core:contentnode_detail', { id: id('nope') })).rejects.toMatchObject({
      response: { status: 404 },
    });
  });

  it("lists the channels' roots, as the library page asks", async () => {
    const roots = await get('kolibri:core:contentnode_list', {
      params: { parent__isnull: true, include_coach_content: false },
    });

    expect(titles(roots)).toEqual(['Algebra', 'Geometry']);
    expect(fetchedPaths()).not.toContain(`index/${ALGEBRA}.json`);
  });

  it("gives the whole library's labels without loading every index", async () => {
    const page = await get('kolibri:core:contentnode_list', { params: { max_results: 1 } });

    expect(page.labels).toEqual(LABELS);
    expect(page.results).toHaveLength(1);
    expect(page.more).toEqual({ max_results: '1', cursor: '1' });
    expect(fetchedPaths().filter(path => path.startsWith('index/'))).toEqual([]);
  });

  it('searches titles and descriptions for every word, leaving out coach content', async () => {
    const results = await get('kolibri:core:contentnode_list', {
      params: {
        question: 'the equations',
        include_coach_content: false,
        kind: 'content',
        max_results: 25,
      },
    });

    // In lft order across channels, as Kolibri pages them
    expect(titles(results.results)).toEqual([
      'Triangles and equations',
      'Solving equations',
      'Practice equations',
    ]);
    expect(results.more).toBeNull();
    expect(results.labels.learning_activities).toEqual(['watch', 'practice']);

    const balanced = await get('kolibri:core:contentnode_list', {
      params: { search: 'balance equations', max_results: 25 },
    });
    expect(titles(balanced.results)).toEqual(['Solving equations']);
  });

  it('filters by labels, and gives the labels of what it found', async () => {
    const results = await get('kolibri:core:contentnode_list', {
      params: { learning_activities: 'watch', max_results: 25, tree_id: 1 },
    });

    expect(titles(results.results)).toEqual(['Solving equations']);
    expect(results.labels.learning_activities).toEqual(['watch']);
    expect(fetchedPaths()).not.toContain(`index/${GEOMETRY}.json`);
  });

  it('pages search results, and gives the next page from the query it returns', async () => {
    const first = await get('kolibri:core:contentnode_list', {
      params: { search: 'lesson', kind: 'content', max_results: 10 },
    });
    const second = await get('kolibri:core:contentnode_list', { params: first.more });

    expect(first.results).toHaveLength(10);
    expect(titles(second.results)).toEqual(['Lesson 10', 'Lesson 11', 'Lesson 12']);
    expect(second.more).toBeNull();
  });

  it("gives a topic's tree a page of children at a time, as Kolibri does", async () => {
    const params = { include_coach_content: false, exclude_modalities: 'COURSE' };
    const root = await get('kolibri:core:contentnode_tree_detail', { id: id('a1'), params });

    const [equations, lessonsTopic] = root.children.results;
    expect(titles(equations.children.results)).toEqual(['Solving equations', 'Practice equations']);
    expect(lessonsTopic.children.results).toHaveLength(12);
    expect(lessonsTopic.children.more).toEqual({
      id: id('ls'),
      params: {
        include_coach_content: 'false',
        exclude_modalities: 'COURSE',
        next__gt: lessonsTopic.children.results[11].rght,
        depth: 1,
      },
    });

    const more = await get('kolibri:core:contentnode_tree_detail', {
      id: lessonsTopic.children.more.id,
      params: lessonsTopic.children.more.params,
    });
    expect(titles(more.children.results)).toEqual(['Lesson 12']);
    // Resources have no children to look for
    expect(fetchedPaths()).not.toContain(`children/${id('eqv')}.json`);
  });

  it('follows a chain of only children down the tree', async () => {
    const topic = await get('kolibri:core:contentnode_tree_detail', { id: id('one') });

    const [deep] = topic.children.results;
    expect(deep.id).toEqual(id('deep'));
    expect(deep.children.results.map(node => node.id)).toEqual([id('leaf')]);
  });

  it('recommends the resources beside one', async () => {
    const recommended = await get('kolibri:core:contentnode_recommendations_for', {
      id: id('eqv'),
      params: { include_coach_content: false },
    });

    expect(titles(recommended)).toEqual(['Practice equations']);
  });

  it('tracks progress through a session with an exercise', async () => {
    const started = (
      await client.post(urls['kolibri:core:trackprogress_list'](), {
        node_id: id('eqx'),
        mastery_model: { type: 'm_of_n', m: 1, n: 1 },
      })
    ).data;
    expect(started).toMatchObject({
      progress: 0,
      complete: false,
      pastattempts: [],
      mastery_criterion: { type: 'm_of_n', m: 1, n: 1 },
      context: { node_id: id('eqx') },
    });

    const answer = { userInput: { 'numeric-input 1': { currentValue: '2' } } };
    const updated = (
      await client.put(urls['kolibri:core:trackprogress_detail'](started.session_id), {
        progress: 1,
        time_spent_delta: 5,
        interactions: [{ item: 'q1', correct: 1, complete: true, time_spent: 5, answer }],
      })
    ).data;

    expect(updated.complete).toBe(true);
    expect(updated.attempts).toEqual([
      {
        id: expect.stringMatching(/^[0-9a-f]{32}$/),
        item: 'q1',
        correct: 1,
        complete: true,
        hinted: false,
        error: false,
        answer,
        time_spent: 5,
      },
    ]);
  });

  it('answers as a guest whose session is the only one there is', async () => {
    const session = (await client.put(urls['kolibri:core:session_detail']('current'), {})).data;

    expect(session).toMatchObject({ id: 'current', kind: ['anonymous'], user_id: null });
  });

  it('answers 404 for what a static library cannot do', async () => {
    await expect(client.get(urls['kolibri:core:facilityuser_list']())).rejects.toMatchObject({
      response: { status: 404 },
    });
  });
});
