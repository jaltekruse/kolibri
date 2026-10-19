import { fireEvent, render, screen, within } from '@testing-library/vue';
import VueRouter from 'vue-router';
import { ref } from 'vue';
// eslint-disable-next-line import-x/named
import useSnackbar, { useSnackbarMock } from 'kolibri/composables/useSnackbar';
import QuickAssignmentResource from 'kolibri-common/apiResources/QuickAssignmentResource';
import { quickAssignStrings } from 'kolibri-common/strings/quickAssignStrings';
import { PageNames } from '../../../constants';
import QuickAssignmentList from '../QuickAssignmentList';

jest.mock('kolibri/composables/useSnackbar');
jest.mock('kolibri-common/apiResources/QuickAssignmentResource');

const {
  copyLinkAction$,
  joinedCountLabel$,
  linkCopiedMessage$,
  linkOpenLabel$,
  viewResultsAction$,
} = quickAssignStrings;

const ASSIGNMENT = {
  id: 'lesson-id',
  title: 'Two-step equations',
  link: 'http://school.example/kolibri/join/abc',
  learner_count: 3,
  is_open: true,
  classroom_id: 'class-id',
};

function renderList() {
  const router = new VueRouter({
    routes: [
      { name: PageNames.LESSON_SUMMARY, path: '/:classId/lessons/:lessonId' },
      { path: '/', component: QuickAssignmentList },
    ],
  });
  return render(QuickAssignmentList, { props: { assignments: [ASSIGNMENT] }, routes: router });
}

describe('QuickAssignmentList', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('shows each link, who joined, and where to see their work', () => {
    renderList();

    const assignment = screen.getByRole('listitem');
    expect(within(assignment).getByRole('heading', { name: ASSIGNMENT.title })).toBeInTheDocument();
    expect(within(assignment).getByTestId('share-link')).toHaveTextContent(ASSIGNMENT.link);
    expect(assignment).toHaveTextContent(joinedCountLabel$({ count: 3 }));
    expect(within(assignment).getByRole('link', { name: viewResultsAction$() })).toHaveAttribute(
      'href',
      '#/class-id/lessons/lesson-id',
    );
  });

  it('copies a link', async () => {
    const writeText = jest.fn().mockResolvedValue();
    Object.assign(navigator, { clipboard: { writeText } });
    const snackbar = { snackbarIsVisible: ref(false), snackbarOptions: ref({}) };
    useSnackbar.mockImplementation(() => useSnackbarMock(snackbar));
    renderList();

    await fireEvent.click(screen.getByRole('button', { name: copyLinkAction$() }));

    expect(writeText).toHaveBeenCalledWith(ASSIGNMENT.link);
    expect(snackbar.snackbarOptions.value.text).toBe(linkCopiedMessage$());
  });

  it('stops new students joining', async () => {
    const closed = { ...ASSIGNMENT, is_open: false };
    QuickAssignmentResource.update.mockResolvedValue(closed);
    const { emitted } = renderList();

    await fireEvent.click(screen.getByRole('checkbox', { name: linkOpenLabel$() }));

    expect(QuickAssignmentResource.update).toHaveBeenCalledWith(ASSIGNMENT.id, {
      is_open: false,
    });
    expect(emitted().updated).toEqual([[closed]]);
  });
});
