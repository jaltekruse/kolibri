import { render, screen, waitFor, fireEvent } from '@testing-library/vue';
import VueRouter from 'vue-router';
import makeStore from '../../../../__tests__/utils/makeStore';
import store from '../../../../store';
import ContentSummaryLogResource from '../../../../apiResources/contentSummaryLog';
import ContentFeedbackLogResource from '../../../../apiResources/contentFeedbackLog';
import LessonResourceReviewPage from '../LessonResourceReviewPage';

jest.mock('kolibri/router', () => ({
  getRoute: (name, params, query) => ({ name, params, query }),
}));
jest.mock('../../../CoachAppBarPage', () => ({
  name: 'CoachAppBarPage',
  render(h) {
    return h('div', this.$slots.default);
  },
}));
jest.mock('../../../common/BackLink', () => ({
  name: 'BackLink',
  render(h) {
    return h('div');
  },
}));
jest.mock('../../../../apiResources/contentSummaryLog', () => ({ list: jest.fn() }));
jest.mock('../../../../apiResources/contentFeedbackLog', () => ({
  list: jest.fn(),
  create: jest.fn(),
}));

const RESOURCE = { id: 'node', content_id: 'content', channel_id: 'channel', title: 'Free Math' };

// Stands in for the resource, which runs in a sandboxed iframe: shows what it was given,
// and changes its storage when asked
const ContentViewer = {
  name: 'ContentViewer',
  props: { extraFields: { type: Object, default: () => ({}) } },
  data: () => ({ storage: '{}' }),
  template: `
    <div>
      <pre data-testid="review">{{ extraFields.contentState.localStorage['kolibri:review'] }}</pre>
      <textarea data-testid="storage" v-model="storage" />
      <button
        data-testid="save-storage"
        @click="$emit('updateContentState', { localStorage: JSON.parse(storage) })"
      />
    </div>
  `,
};

function renderPage() {
  store.replaceState(makeStore().state);
  store.state.classSummary = {
    ...store.state.classSummary,
    id: 'class',
    name: 'Class',
    lessonMap: { lesson: { id: 'lesson', title: 'Lesson', assignments: ['class'] } },
    learnerMap: {
      ada: { id: 'ada', name: 'Ada' },
      bo: { id: 'bo', name: 'Bo' },
    },
  };
  store.state.resourceDetail = { resource: RESOURCE };
  const router = new VueRouter({
    routes: [{ path: '/:classId/lessons/:lessonId/resources/:resourceId/review', name: 'review' }],
  });
  router.push('/class/lessons/lesson/resources/content-in-lesson/review');
  return render(LessonResourceReviewPage, {
    store,
    routes: router,
    // eslint-disable-next-line kolibri/tests-no-stubs
    stubs: { ContentViewer },
  });
}

describe('LessonResourceReviewPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    ContentSummaryLogResource.list.mockResolvedValue([
      { user: 'ada', extra_fields: { contentState: { localStorage: { work: '1' } } } },
    ]);
    ContentFeedbackLogResource.list.mockResolvedValue([{ user: 'bo', data: { score: 2 } }]);
    ContentFeedbackLogResource.create.mockResolvedValue({});
  });

  it("gives the resource the lesson's learners' work and feedback to review", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('review')).not.toBeEmptyDOMElement());
    expect(JSON.parse(screen.getByTestId('review').textContent)).toEqual({
      learners: [
        { id: 'ada', name: 'Ada', work: { work: '1' }, feedback: null },
        { id: 'bo', name: 'Bo', work: null, feedback: { score: 2 } },
      ],
    });
    expect(ContentSummaryLogResource.list).toHaveBeenCalledWith({
      content_id: 'content-in-lesson',
      classroom: 'class',
    });
  });

  it('saves feedback the resource gives a learner', async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('save-storage'));
    await fireEvent.update(
      screen.getByTestId('storage'),
      JSON.stringify({ 'kolibri:feedback:ada': JSON.stringify({ score: 5 }), other: 'x' }),
    );
    await fireEvent.click(screen.getByTestId('save-storage'));
    expect(ContentFeedbackLogResource.create).toHaveBeenCalledWith({
      user: 'ada',
      content_id: 'content-in-lesson',
      channel_id: 'channel',
      data: { score: 5 },
    });
  });

  it("doesn't save feedback that hasn't changed", async () => {
    renderPage();
    await waitFor(() => screen.getByTestId('save-storage'));
    await fireEvent.update(
      screen.getByTestId('storage'),
      JSON.stringify({ 'kolibri:feedback:bo': JSON.stringify({ score: 2 }) }),
    );
    await fireEvent.click(screen.getByTestId('save-storage'));
    expect(ContentFeedbackLogResource.create).not.toHaveBeenCalled();
  });
});
