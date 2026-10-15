import { render, screen, within } from '@testing-library/vue';
import LessonResource from 'kolibri-common/apiResources/LessonResource';
import LessonResponseResource from 'kolibri-common/apiResources/LessonResponseResource';
import LessonResponseFeedbackResource from 'kolibri-common/apiResources/LessonResponseFeedbackResource';
import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
import LessonResourceResponses from '../index';

jest.mock('kolibri-common/apiResources/LessonResource');
jest.mock('kolibri-common/apiResources/LessonResponseResource');
jest.mock('kolibri-common/apiResources/LessonResponseFeedbackResource');

const { learnerAnswersLabel$, learnerAnswersLoadError$, notStartedStatus$, submittedStatus$ } =
  lessonResponsesStrings;

const LEARNERS = [
  { id: 'learner-1', name: 'Ada' },
  { id: 'learner-2', name: 'Grace' },
];
const RESOURCE = {
  contentnode_id: 'contentnode-id',
  content_id: 'content-id',
  channel_id: 'channel-id',
  prompts: [{ id: 'prompt-1', text: 'Answer question 1 on page 2' }],
};

function renderResponses() {
  return render(LessonResourceResponses, {
    props: { lessonId: 'lesson-id', contentId: 'content-id', learners: LEARNERS },
  });
}

describe('LessonResourceResponses', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("shows each learner's answers to the resource's questions", async () => {
    LessonResource.retrieve.mockResolvedValue({ resources: [RESOURCE] });
    LessonResponseResource.list.mockResolvedValue([
      {
        id: 'attempt-1',
        user: 'learner-1',
        item: 'prompt-1',
        answer: { text: 'Chlorophyll' },
        complete: true,
      },
    ]);
    LessonResponseFeedbackResource.list.mockResolvedValue([]);
    renderResponses();

    const ada = await screen.findByTestId('learner-learner-1');
    expect(screen.getByRole('heading', { name: learnerAnswersLabel$() })).toBeInTheDocument();
    expect(within(ada).getByTestId('status')).toHaveTextContent(submittedStatus$());
    expect(within(ada).getByTestId('answer-prompt-1')).toHaveTextContent('Chlorophyll');
    const grace = screen.getByTestId('learner-learner-2');
    expect(within(grace).getByTestId('status')).toHaveTextContent(notStartedStatus$());
    expect(LessonResponseResource.list).toHaveBeenCalledWith({
      lesson_id: 'lesson-id',
      contentnode_id: 'contentnode-id',
    });
  });

  it('shows an error when the answers fail to load', async () => {
    LessonResource.retrieve.mockResolvedValue({ resources: [RESOURCE] });
    LessonResponseResource.list.mockRejectedValue(new Error('Network error'));
    LessonResponseFeedbackResource.list.mockResolvedValue([]);
    renderResponses();

    expect(await screen.findByRole('alert')).toHaveTextContent(learnerAnswersLoadError$());
  });

  it('shows nothing for a resource without questions', async () => {
    LessonResource.retrieve.mockResolvedValue({
      resources: [{ ...RESOURCE, prompts: [] }],
    });
    renderResponses();
    // Let the lesson request settle
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(LessonResource.retrieve).toHaveBeenCalledWith('lesson-id');
    expect(screen.queryByRole('heading', { name: learnerAnswersLabel$() })).not.toBeInTheDocument();
    expect(LessonResponseResource.list).not.toHaveBeenCalled();
  });
});
