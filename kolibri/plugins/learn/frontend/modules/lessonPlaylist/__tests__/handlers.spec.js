import ContentNodeResource from 'kolibri-common/apiResources/ContentNodeResource';
import ContentNodeProgressResource from 'kolibri-common/apiResources/ContentNodeProgressResource';
import useContentNodeProgress from '../../../composables/useContentNodeProgress';
import { LearnerLessonResource } from '../../../apiResources';
import { showLessonPlaylist } from '../handlers';

jest.mock('kolibri-common/apiResources/ContentNodeResource', () => ({
  fetchLessonResources: jest.fn(),
}));
jest.mock('kolibri-common/apiResources/ContentNodeProgressResource', () => ({ list: jest.fn() }));
jest.mock('../../../apiResources', () => ({ LearnerLessonResource: { retrieve: jest.fn() } }));
jest.mock('kolibri/composables/useUser', () => () => ({ isUserLoggedIn: true }));

const NODE = { id: 'node', content_id: 'content' };

function makeStore() {
  const state = {};
  return {
    state,
    commit(mutation, payload) {
      state[mutation] = payload;
    },
  };
}

describe('showLessonPlaylist', () => {
  beforeEach(() => {
    ContentNodeProgressResource.list.mockResolvedValue([]);
    ContentNodeResource.fetchLessonResources.mockResolvedValue([NODE]);
  });

  it('shows a resource with progress for each lesson under its content_id in the lesson', async () => {
    LearnerLessonResource.retrieve.mockResolvedValue({
      id: 'lesson',
      resources: [{ contentnode_id: 'node', content_id: 'content-in-lesson', progress: 0.5 }],
    });
    const store = makeStore();
    await showLessonPlaylist(store, { lessonId: 'lesson' });
    const node = store.state['lessonPlaylist/SET_LESSON_CONTENTNODES'].node;
    expect(node.content_id).toBe('content-in-lesson');
    expect(useContentNodeProgress().contentNodeProgressMap['content-in-lesson']).toBe(0.5);
  });

  it('keeps the content_id of other resources', async () => {
    LearnerLessonResource.retrieve.mockResolvedValue({
      id: 'lesson',
      resources: [{ contentnode_id: 'node', content_id: 'content', progress: 0 }],
    });
    const store = makeStore();
    await showLessonPlaylist(store, { lessonId: 'lesson' });
    expect(store.state['lessonPlaylist/SET_LESSON_CONTENTNODES'].node.content_id).toBe('content');
  });
});
