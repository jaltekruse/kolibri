import { fireEvent, render, screen } from '@testing-library/vue';
// eslint-disable-next-line import-x/named
import useUser, { useUserMock } from 'kolibri/composables/useUser';
import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
import ContentNodeResource from 'kolibri-common/apiResources/ContentNodeResource';
import QuickAssignmentResource from 'kolibri-common/apiResources/QuickAssignmentResource';
import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
import { quickAssignStrings } from 'kolibri-common/strings/quickAssignStrings';
import QuickAssignForm from '../QuickAssignForm';

jest.mock('kolibri/composables/useUser');
jest.mock('kolibri-common/apiResources/ContentNodeResource');
jest.mock('kolibri-common/apiResources/QuickAssignmentResource');

const {
  addExerciseAction$,
  assignmentTitleLabel$,
  createError$,
  createLinkAction$,
  freeMathOption$,
  quickAssignClassName$,
  removeExerciseAction$,
  searchExercisesLabel$,
} = quickAssignStrings;
const { problemNumbersLabel$, webPageUrlLabel$ } = lessonResponsesStrings;
const { searchLabel$ } = coreStrings;

const COACH = 'Ana Rivera';
const EXERCISE = { id: 'exercise-id', title: 'Two-step equations' };
const CREATED = {
  id: 'lesson-id',
  title: EXERCISE.title,
  link: 'http://school.example/kolibri/join/abc',
  learner_count: 0,
  is_open: true,
  classroom_id: 'class-id',
};

describe('QuickAssignForm', () => {
  beforeEach(() => {
    useUser.mockImplementation(() => useUserMock({ full_name: COACH, isCoach: true }));
    QuickAssignmentResource.create.mockResolvedValue(CREATED);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('assigns exercises found in the library, titled after the first', async () => {
    ContentNodeResource.list.mockResolvedValue({ results: [EXERCISE], more: null });
    const { emitted } = render(QuickAssignForm);

    await fireEvent.update(
      screen.getByRole('searchbox', { name: searchExercisesLabel$() }),
      'equations',
    );
    await fireEvent.click(screen.getByRole('button', { name: searchLabel$() }));
    await fireEvent.click(
      await screen.findByRole('button', { name: addExerciseAction$({ title: EXERCISE.title }) }),
    );

    expect(screen.getByRole('textbox', { name: assignmentTitleLabel$() })).toHaveValue(
      EXERCISE.title,
    );
    await fireEvent.click(screen.getByRole('button', { name: createLinkAction$() }));

    expect(ContentNodeResource.list).toHaveBeenCalledWith(
      expect.objectContaining({ search: 'equations', kind: 'exercise' }),
    );
    expect(QuickAssignmentResource.create).toHaveBeenCalledWith({
      title: EXERCISE.title,
      classroom_name: quickAssignClassName$({ name: COACH }),
      exercise_ids: [EXERCISE.id],
    });
    expect(emitted().created).toEqual([[CREATED]]);
  });

  it('needs an exercise and a title', async () => {
    render(QuickAssignForm);

    await fireEvent.click(screen.getByRole('button', { name: createLinkAction$() }));

    expect(QuickAssignmentResource.create).not.toHaveBeenCalled();
  });

  it('starts with an exercise a coach chose to quick assign in Learn', async () => {
    ContentNodeResource.retrieve.mockResolvedValue(EXERCISE);
    render(QuickAssignForm, { props: { exerciseId: EXERCISE.id } });

    expect(
      await screen.findByRole('button', { name: removeExerciseAction$({ title: EXERCISE.title }) }),
    ).toBeInTheDocument();
    expect(ContentNodeResource.retrieve).toHaveBeenCalledWith(EXERCISE.id);
  });

  it('lets a coach take an exercise back out', async () => {
    ContentNodeResource.retrieve.mockResolvedValue(EXERCISE);
    render(QuickAssignForm, { props: { exerciseId: EXERCISE.id } });

    await fireEvent.click(
      await screen.findByRole('button', { name: removeExerciseAction$({ title: EXERCISE.title }) }),
    );
    await fireEvent.click(screen.getByRole('button', { name: createLinkAction$() }));

    expect(QuickAssignmentResource.create).not.toHaveBeenCalled();
  });

  it('assigns problems from a web page to work in Free Math', async () => {
    render(QuickAssignForm);

    await fireEvent.click(screen.getByRole('radio', { name: freeMathOption$() }));
    await fireEvent.update(
      screen.getByRole('textbox', { name: webPageUrlLabel$() }),
      'https://example.org/equations',
    );
    await fireEvent.update(
      screen.getByRole('textbox', { name: problemNumbersLabel$() }),
      '1-9 by 2',
    );
    await fireEvent.update(screen.getByRole('textbox', { name: assignmentTitleLabel$() }), 'Odds');
    await fireEvent.click(screen.getByRole('button', { name: createLinkAction$() }));

    expect(QuickAssignmentResource.create).toHaveBeenCalledWith({
      title: 'Odds',
      classroom_name: quickAssignClassName$({ name: COACH }),
      web_page: {
        url: 'https://example.org/equations',
        instructions: '',
        problem_numbers: '1-9 by 2',
      },
    });
  });

  it('says when the assignment could not be made', async () => {
    ContentNodeResource.retrieve.mockResolvedValue(EXERCISE);
    QuickAssignmentResource.create.mockRejectedValue({ response: { status: 500 } });
    const { emitted } = render(QuickAssignForm, { props: { exerciseId: EXERCISE.id } });

    await screen.findByRole('button', { name: removeExerciseAction$({ title: EXERCISE.title }) });
    await fireEvent.click(screen.getByRole('button', { name: createLinkAction$() }));

    expect(await screen.findByRole('alert')).toHaveTextContent(createError$());
    expect(emitted().created).toBeUndefined();
  });
});
