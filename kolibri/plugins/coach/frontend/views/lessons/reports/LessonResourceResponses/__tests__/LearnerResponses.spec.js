import { render, screen, fireEvent, waitFor } from '@testing-library/vue';
import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
import LessonResponseFeedbackResource from 'kolibri-common/apiResources/LessonResponseFeedbackResource';
import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
import LearnerResponses from '../LearnerResponses';

jest.mock('kolibri-common/apiResources/LessonResponseFeedbackResource');

const {
  addFeedbackAction$,
  answerFeedbackLabel$,
  editFeedbackAction$,
  notStartedStatus$,
  overallFeedbackLabel$,
  submittedStatus$,
} = lessonResponsesStrings;
const { saveAction$ } = coreStrings;

const PROMPTS = [
  { id: 'prompt-1', text: 'Answer question 1 on page 2' },
  { id: 'prompt-2', text: 'Summarize section 3' },
];

function renderLearnerResponses(props = {}) {
  return render(LearnerResponses, {
    props: {
      lessonId: 'lesson-id',
      contentnodeId: 'contentnode-id',
      learnerId: 'learner-id',
      learnerName: 'Ada',
      prompts: PROMPTS,
      answers: { 'prompt-1': 'Chlorophyll absorbs light' },
      submitted: true,
      feedback: null,
      ...props,
    },
  });
}

describe('LearnerResponses', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("shows the learner's answers and status", () => {
    renderLearnerResponses();
    expect(screen.getByTestId('status')).toHaveTextContent(submittedStatus$());
    expect(screen.getByTestId('answer-prompt-1')).toHaveTextContent('Chlorophyll absorbs light');
  });

  it('shows no answers or feedback action for a learner who has not started', () => {
    renderLearnerResponses({ answers: {}, submitted: false });
    expect(screen.getByTestId('status')).toHaveTextContent(notStartedStatus$());
    expect(screen.queryByTestId('answer-prompt-1')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: addFeedbackAction$() })).not.toBeInTheDocument();
  });

  it('creates feedback for the learner', async () => {
    const savedFeedback = {
      id: 'feedback-id',
      user: 'learner-id',
      comment: 'Good start',
      prompt_comments: { 'prompt-1': 'Which pigment?' },
    };
    LessonResponseFeedbackResource.create.mockResolvedValue(savedFeedback);
    const { emitted } = renderLearnerResponses();

    await fireEvent.click(screen.getByRole('button', { name: addFeedbackAction$() }));
    const [firstAnswerFeedback] = screen.getAllByRole('textbox', {
      name: answerFeedbackLabel$(),
    });
    await fireEvent.update(firstAnswerFeedback, 'Which pigment?');
    await fireEvent.update(
      screen.getByRole('textbox', { name: overallFeedbackLabel$() }),
      ' Good start ',
    );
    await fireEvent.click(screen.getByRole('button', { name: saveAction$() }));

    await waitFor(() => expect(emitted().feedbackSaved).toEqual([[savedFeedback]]));
    expect(LessonResponseFeedbackResource.create).toHaveBeenCalledWith({
      user: 'learner-id',
      lesson_id: 'lesson-id',
      contentnode_id: 'contentnode-id',
      comment: 'Good start',
      prompt_comments: { 'prompt-1': 'Which pigment?' },
    });
  });

  it('updates existing feedback', async () => {
    const feedback = {
      id: 'feedback-id',
      user: 'learner-id',
      comment: 'Good start',
      prompt_comments: { 'prompt-1': 'Which pigment?' },
    };
    LessonResponseFeedbackResource.update.mockResolvedValue({ ...feedback, comment: 'Great' });
    renderLearnerResponses({ feedback });

    expect(screen.getByTestId('overall-feedback')).toHaveTextContent('Good start');
    expect(screen.getByTestId('feedback-prompt-1')).toHaveTextContent('Which pigment?');

    await fireEvent.click(screen.getByRole('button', { name: editFeedbackAction$() }));
    await fireEvent.update(
      screen.getByRole('textbox', { name: overallFeedbackLabel$() }),
      'Great',
    );
    await fireEvent.click(screen.getByRole('button', { name: saveAction$() }));

    await waitFor(() =>
      expect(LessonResponseFeedbackResource.update).toHaveBeenCalledWith('feedback-id', {
        comment: 'Great',
        prompt_comments: { 'prompt-1': 'Which pigment?' },
      }),
    );
    expect(LessonResponseFeedbackResource.create).not.toHaveBeenCalled();
  });
});
