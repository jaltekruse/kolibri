import { render, screen, fireEvent, waitFor, within } from '@testing-library/vue';
import LessonResponseResource from 'kolibri-common/apiResources/LessonResponseResource';
import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
import { AUTOSAVE_DELAY } from '../../../composables/useLessonResponses';
import LessonResponsesPanel from '../LessonResponsesPanel';

jest.mock('kolibri-common/apiResources/LessonResponseResource');
// The editor's page URL
jest.mock('kolibri/urls');

const {
  loadErrorStatus$,
  mathEditorLabel$,
  submitAnswersAction$,
  submittedStatus$,
  unansweredQuestionsWarning$,
} = lessonResponsesStrings;

const LESSON_ID = 'lesson-id';
const CONTENTNODE_ID = 'contentnode-id';
const PROMPTS = [
  { id: 'prompt-1', text: 'What is the main idea of section 1?' },
  { id: 'prompt-2', text: 'Solve problem 3 on page 4' },
];
// Stand in for base64 encoded Free Math documents
const SAVED_WORK = 'c2F2ZWQgd29yaw==';
const NEW_WORK = 'bmV3IHdvcms=';

function response(item, document, complete = false) {
  return {
    id: `attempt-${item}`,
    user: 'learner',
    item,
    answer: { free_math: document },
    complete,
  };
}

function renderPanel({ responses = [] } = {}) {
  LessonResponseResource.list.mockResolvedValue(responses);
  LessonResponseResource.saveAnswers.mockResolvedValue([]);
  return render(LessonResponsesPanel, {
    props: {
      lessonId: LESSON_ID,
      contentnodeId: CONTENTNODE_ID,
      prompts: PROMPTS,
      title: 'Photosynthesis reading',
    },
  });
}

// A message from Free Math, running in the editor frame
function fromEditor(frame, data) {
  window.dispatchEvent(
    new MessageEvent('message', {
      data: { source: 'free-math', ...data },
      origin: window.location.origin,
      source: frame.contentWindow,
    }),
  );
}

// Waits for the editor, and records the messages sent to it. Like Free Math, it
// sends `unsentWork` when asked to send its pending work.
async function openEditor({ unsentWork = {} } = {}) {
  const frame = await screen.findByTitle(mathEditorLabel$());
  const sent = jest.spyOn(frame.contentWindow, 'postMessage').mockImplementation(message => {
    if (message.type === 'flush') {
      fromEditor(frame, { type: 'save', answers: unsentWork });
      fromEditor(frame, { type: 'flushed', requestId: message.requestId });
    }
  });
  fromEditor(frame, { type: 'ready' });
  return { frame, sent };
}

function loadMessages(sent) {
  return sent.mock.calls.map(([message]) => message).filter(m => m.type === 'load-student');
}

async function submitAnswers() {
  await fireEvent.click(screen.getByRole('button', { name: submitAnswersAction$() }));
  const dialog = screen.getByRole('dialog');
  await fireEvent.click(within(dialog).getByRole('button', { name: submitAnswersAction$() }));
}

describe('LessonResponsesPanel', () => {
  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  it("opens the questions in the editor with the learner's saved work", async () => {
    renderPanel({ responses: [response('prompt-1', SAVED_WORK)] });
    const { sent } = await openEditor();

    expect(LessonResponseResource.list).toHaveBeenCalledWith({
      lesson_id: LESSON_ID,
      contentnode_id: CONTENTNODE_ID,
    });
    expect(loadMessages(sent)).toEqual([
      {
        source: 'free-math-host',
        type: 'load-student',
        title: 'Photosynthesis reading',
        readOnly: false,
        problems: [
          { key: 'prompt-1', number: '1', prompt: PROMPTS[0].text, content: SAVED_WORK },
          { key: 'prompt-2', number: '2', prompt: PROMPTS[1].text, content: '' },
        ],
      },
    ]);
  });

  it('saves work from the editor automatically', async () => {
    renderPanel();
    const { frame } = await openEditor();
    jest.useFakeTimers();
    fromEditor(frame, { type: 'save', answers: { 'prompt-2': NEW_WORK } });
    expect(LessonResponseResource.saveAnswers).not.toHaveBeenCalled();
    jest.advanceTimersByTime(AUTOSAVE_DELAY);
    await waitFor(() =>
      expect(LessonResponseResource.saveAnswers).toHaveBeenCalledWith({
        lessonId: LESSON_ID,
        contentnodeId: CONTENTNODE_ID,
        answers: { 'prompt-2': NEW_WORK },
      }),
    );
  });

  it('submits the answers, with work the editor had not sent yet, after the learner confirms', async () => {
    renderPanel({ responses: [response('prompt-1', SAVED_WORK)] });
    const { sent } = await openEditor({ unsentWork: { 'prompt-2': NEW_WORK } });
    await submitAnswers();

    expect(await screen.findByTestId('submitted-status')).toHaveTextContent(submittedStatus$());
    expect(LessonResponseResource.saveAnswers.mock.calls).toEqual([
      [{ lessonId: LESSON_ID, contentnodeId: CONTENTNODE_ID, answers: { 'prompt-2': NEW_WORK } }],
      [{ lessonId: LESSON_ID, contentnodeId: CONTENTNODE_ID, answers: {}, submit: true }],
    ]);
    // The editor shows the submitted work, which can no longer be changed
    const reloaded = loadMessages(sent).pop();
    expect(reloaded.readOnly).toBe(true);
    expect(reloaded.problems.map(problem => problem.content)).toEqual([SAVED_WORK, NEW_WORK]);
    expect(screen.queryByRole('button', { name: submitAnswersAction$() })).not.toBeInTheDocument();
  });

  it('warns about unanswered questions before submitting', async () => {
    renderPanel({ responses: [response('prompt-1', SAVED_WORK)] });
    await openEditor();
    await fireEvent.click(screen.getByRole('button', { name: submitAnswersAction$() }));
    expect(screen.getByRole('dialog')).toHaveTextContent(unansweredQuestionsWarning$({ count: 1 }));
  });

  it('cannot submit before any question is answered', async () => {
    renderPanel();
    await openEditor();
    expect(screen.getByRole('button', { name: submitAnswersAction$() })).toBeDisabled();
  });

  it('shows submitted work, with any grading in it, without letting the learner change it', async () => {
    renderPanel({ responses: [response('prompt-1', SAVED_WORK, true)] });
    const { sent } = await openEditor();

    expect(screen.getByTestId('submitted-status')).toHaveTextContent(submittedStatus$());
    expect(loadMessages(sent)[0].readOnly).toBe(true);
    expect(screen.queryByRole('button', { name: submitAnswersAction$() })).not.toBeInTheDocument();
  });

  it('shows an error when the answers fail to load', async () => {
    LessonResponseResource.list.mockRejectedValue(new Error('Network error'));
    render(LessonResponsesPanel, {
      props: { lessonId: LESSON_ID, contentnodeId: CONTENTNODE_ID, prompts: PROMPTS },
    });
    expect(await screen.findByRole('alert')).toHaveTextContent(loadErrorStatus$());
    expect(screen.queryByTitle(mathEditorLabel$())).not.toBeInTheDocument();
  });
});
