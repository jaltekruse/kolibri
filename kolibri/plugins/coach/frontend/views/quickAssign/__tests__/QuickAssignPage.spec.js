import { fireEvent, render, screen, within } from '@testing-library/vue';
import VueRouter from 'vue-router';
// eslint-disable-next-line import-x/named
import useUser, { useUserMock } from 'kolibri/composables/useUser';
import ContentNodeResource from 'kolibri-common/apiResources/ContentNodeResource';
import QuickAssignmentResource from 'kolibri-common/apiResources/QuickAssignmentResource';
import { quickAssignStrings } from 'kolibri-common/strings/quickAssignStrings';
import { PageNames } from '../../../constants';
import QuickAssignPage from '../QuickAssignPage';

jest.mock('kolibri/composables/useUser');
jest.mock('kolibri-common/apiResources/ContentNodeResource');
jest.mock('kolibri-common/apiResources/QuickAssignmentResource');
// The app bar needs the whole coach app around it
jest.mock('../../CoachAppBarPage', () => ({
  name: 'CoachAppBarPage',
  render(h) {
    return h('div', this.$slots.default);
  },
}));

const { createLinkAction$, noQuickAssignments$, removeExerciseAction$ } = quickAssignStrings;

const EXERCISE = { id: 'exercise-id', title: 'Two-step equations' };
const CREATED = {
  id: 'lesson-id',
  title: EXERCISE.title,
  link: 'http://school.example/kolibri/join/abc',
  learner_count: 0,
  is_open: true,
  classroom_id: 'class-id',
};

async function renderPage(query = {}) {
  const router = new VueRouter({
    routes: [
      { name: PageNames.QUICK_ASSIGN, path: '/quick-assign', component: QuickAssignPage },
      { name: PageNames.LESSON_SUMMARY, path: '/:classId/lessons/:lessonId' },
    ],
  });
  await router.push({ name: PageNames.QUICK_ASSIGN, query });
  render({ template: '<router-view />' }, { routes: router });
  return router;
}

describe('QuickAssignPage', () => {
  beforeEach(() => {
    useUser.mockImplementation(() => useUserMock({ full_name: 'Ana Rivera', isCoach: true }));
    ContentNodeResource.retrieve.mockResolvedValue(EXERCISE);
    QuickAssignmentResource.create.mockResolvedValue(CREATED);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('shares the link of an exercise chosen in Learn, then starts afresh', async () => {
    QuickAssignmentResource.list.mockResolvedValue([]);
    const router = await renderPage({ exercise: EXERCISE.id });

    expect(await screen.findByText(noQuickAssignments$())).toBeInTheDocument();
    await screen.findByRole('button', { name: removeExerciseAction$({ title: EXERCISE.title }) });
    await fireEvent.click(screen.getByRole('button', { name: createLinkAction$() }));

    expect(await screen.findByRole('status')).toHaveTextContent(CREATED.link);
    expect(
      within(screen.getByRole('list')).getByRole('heading', { name: CREATED.title }),
    ).toBeInTheDocument();
    expect(screen.queryByText(noQuickAssignments$())).not.toBeInTheDocument();
    expect(router.currentRoute.query).toEqual({});
    expect(
      screen.queryByRole('button', { name: removeExerciseAction$({ title: EXERCISE.title }) }),
    ).not.toBeInTheDocument();
  });

  it('lists the quick assignments made before', async () => {
    QuickAssignmentResource.list.mockResolvedValue([CREATED]);
    await renderPage();

    expect(await screen.findByRole('heading', { name: CREATED.title })).toBeInTheDocument();
  });
});
