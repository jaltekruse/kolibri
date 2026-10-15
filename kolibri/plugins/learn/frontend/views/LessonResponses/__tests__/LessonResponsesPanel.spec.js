import { render, screen, fireEvent, waitFor, within } from '@testing-library/vue';
import LessonResponseResource from 'kolibri-common/apiResources/LessonResponseResource';
import LessonResponseFeedbackResource from 'kolibri-common/apiResources/LessonResponseFeedbackResource';
import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
import { AUTOSAVE_DELAY } from '../../../composables/useLessonResponses';
import LessonResponsesPanel from '../LessonResponsesPanel';

jest.mock('kolibri-common/apiResources/LessonResponseResource');
jest.mock('kolibri-common/apiResources/LessonResponseFeedbackResource');

const {
  answerToQuestionLabel$,
  coachFeedbackLabel$,
  submitAnswersAction$,
  submittedStatus$,
  unansweredQuestionsWarning$,
} = lessonResponsesStrings;

const LESSON_ID = 'lesson-id';
const CONTENTNODE_ID = 'contentnode-id';
const PROMPTS = [
  { id: 'prompt-1', text: 'What is the main idea of section 1?' },
  { id: 'prompt-2', text: 'Answer question 3 on page 4' },
];

function response(item, text, complete = false) {
  return { id: `attempt-${item}`, user: 'learner', item, answer: { text }, complete };
}

function renderPanel({ responses = [], feedback = [] } = {}) {
  LessonResponseResource.list.mockResolvedValue(responses);
  LessonResponseFeedbackResource.list.mockResolvedValue(feedback);
  LessonResponseResource.saveAnswers.mockResolvedValue([]);
  return render(LessonResponsesPanel, {
    props: { lessonId: LESSON_ID, contentnodeId: CONTENTNODE_ID, prompts: PROMPTS },
  });
}

function answerBox(number) {
  return screen.findByRole('textbox', { name: answerToQuestionLabel$({ number }) });
}

describe('LessonResponsesPanel', () => {
  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  it('loads the answers for this lesson resource', async () => {
    renderPanel({ responses: [response('prompt-1', 'A saved answer')] });
    expect(await answerBox(1)).toHaveValue('A saved answer');
    expect(await answerBox(2)).toHaveValue('');
    expect(LessonResponseResource.list).toHaveBeenCalledWith({
      lesson_id: LESSON_ID,
      contentnode_id: CONTENTNODE_ID,
    });
  });

  it('saves a changed answer automatically', async () => {
    jest.useFakeTimers();
    renderPanel();
    await fireEvent.update(await answerBox(2), 'Forty two');
    expect(LessonResponseResource.saveAnswers).not.toHaveBeenCalled();
    jest.advanceTimersByTime(AUTOSAVE_DELAY);
    await waitFor(() =>
      expect(LessonResponseResource.saveAnswers).toHaveBeenCalledWith({
        lessonId: LESSON_ID,
        contentnodeId: CONTENTNODE_ID,
        answers: { 'prompt-2': 'Forty two' },
        submit: false,
      }),
    );
  });

  it('submits the answers after the learner confirms', async () => {
    renderPanel({ responses: [response('prompt-1', 'First answer')] });
    await fireEvent.update(await answerBox(2), 'Second answer');
    await fireEvent.click(screen.getByRole('button', { name: submitAnswersAction$() }));
    const dialog = screen.getByRole('dialog');
    await fireEvent.click(within(dialog).getByRole('button', { name: submitAnswersAction$() }));
    await waitFor(() =>
      expect(LessonResponseResource.saveAnswers).toHaveBeenCalledWith({
        lessonId: LESSON_ID,
        contentnodeId: CONTENTNODE_ID,
        answers: { 'prompt-2': 'Second answer' },
        submit: true,
      }),
    );
    expect(await screen.findByTestId('submitted-status')).toHaveTextContent(submittedStatus$());
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('warns about unanswered questions before submitting', async () => {
    renderPanel({ responses: [response('prompt-1', 'Only answer')] });
    await answerBox(1);
    await fireEvent.click(screen.getByRole('button', { name: submitAnswersAction$() }));
    expect(screen.getByRole('dialog')).toHaveTextContent(unansweredQuestionsWarning$({ count: 1 }));
  });

  it('cannot submit before any question is answered', async () => {
    renderPanel();
    await answerBox(1);
    expect(screen.getByRole('button', { name: submitAnswersAction$() })).toBeDisabled();
  });

  it('shows submitted answers and coach feedback without answer boxes', async () => {
    renderPanel({
      responses: [response('prompt-1', 'Submitted answer', true)],
      feedback: [
        {
          id: 'feedback-id',
          comment: 'Well argued overall',
          prompt_comments: { 'prompt-1': 'Look again at paragraph 2' },
        },
      ],
    });
    expect(await screen.findByTestId('answer-prompt-1')).toHaveTextContent('Submitted answer');
    expect(screen.getByTestId('overall-feedback')).toHaveTextContent('Well argued overall');
    expect(screen.getByTestId('overall-feedback')).toHaveTextContent(coachFeedbackLabel$());
    expect(screen.getByTestId('feedback-prompt-1')).toHaveTextContent('Look again at paragraph 2');
    expect(screen.queryByTestId('feedback-prompt-2')).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });
});
