import { render, screen, waitFor } from '@testing-library/vue';
import LessonResource from 'kolibri-common/apiResources/LessonResource';
import LessonResponseResource from 'kolibri-common/apiResources/LessonResponseResource';
import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
import LessonResourceResponses from '../index';

jest.mock('kolibri-common/apiResources/LessonResource');
jest.mock('kolibri-common/apiResources/LessonResponseResource');
// The editor's page URL
jest.mock('kolibri/urls');

const { gradingEditorLabel$, learnerAnswersLabel$, learnerAnswersLoadError$, noAnswersYetStatus$ } =
  lessonResponsesStrings;

const LEARNERS = [
  { id: 'learner-1', name: 'Ada' },
  { id: 'learner-2', name: 'Grace' },
  { id: 'learner-3', name: 'Katherine' },
];
const RESOURCE = {
  contentnode_id: 'contentnode-id',
  content_id: 'content-id',
  channel_id: 'channel-id',
  prompts: [
    { id: 'prompt-1', text: 'Solve problem 1 on page 2' },
    { id: 'prompt-2', text: 'Solve problem 2 on page 2' },
  ],
};
const LESSON = { title: 'Photosynthesis', resources: [RESOURCE] };
// Stand in for base64 encoded Free Math documents
const ADA_WORK_1 = 'YWRhIDE=';
const ADA_WORK_2 = 'YWRhIDI=';
const GRACE_WORK_2 = 'Z3JhY2UgMg==';
const ADA_GRADED_1 = 'YWRhIDEgZ3JhZGVk';

function response(user, item, document) {
  return { id: `${user}-${item}`, user, item, answer: { free_math: document }, complete: true };
}

function renderResponses({ responses = [] } = {}) {
  LessonResource.retrieve.mockResolvedValue(LESSON);
  LessonResponseResource.list.mockResolvedValue(responses);
  return render(LessonResourceResponses, {
    props: { lessonId: 'lesson-id', contentId: 'content-id', learners: LEARNERS },
  });
}

// A message from Free Math, running in the grading frame
function fromGrader(frame, data) {
  window.dispatchEvent(
    new MessageEvent('message', {
      data: { source: 'free-math', ...data },
      origin: window.location.origin,
      source: frame.contentWindow,
    }),
  );
}

async function openGrader() {
  const frame = await screen.findByTitle(gradingEditorLabel$());
  const sent = jest.spyOn(frame.contentWindow, 'postMessage').mockImplementation(() => {});
  fromGrader(frame, { type: 'ready' });
  return { frame, sent };
}

describe('LessonResourceResponses', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("opens the learners' work in the grading view, grouped by question", async () => {
    renderResponses({
      responses: [
        response('learner-1', 'prompt-1', ADA_WORK_1),
        response('learner-1', 'prompt-2', ADA_WORK_2),
        response('learner-2', 'prompt-2', GRACE_WORK_2),
      ],
    });
    const { sent } = await openGrader();

    expect(screen.getByRole('heading', { name: learnerAnswersLabel$() })).toBeInTheDocument();
    expect(LessonResponseResource.list).toHaveBeenCalledWith({
      lesson_id: 'lesson-id',
      item_id: 'contentnode-id',
    });
    const problem = (prompt, number, content) => ({
      key: prompt.id,
      number,
      prompt: prompt.text,
      content,
    });
    // Learners without answers are left out, as are questions a learner did not answer
    expect(sent).toHaveBeenCalledWith(
      {
        source: 'free-math-host',
        type: 'load-grading',
        title: 'Photosynthesis',
        students: [
          {
            id: 'learner-1',
            name: 'Ada',
            problems: [
              problem(RESOURCE.prompts[0], '1', ADA_WORK_1),
              problem(RESOURCE.prompts[1], '2', ADA_WORK_2),
            ],
          },
          {
            id: 'learner-2',
            name: 'Grace',
            problems: [problem(RESOURCE.prompts[1], '2', GRACE_WORK_2)],
          },
        ],
      },
      window.location.origin,
    );
  });

  it('saves grading from the grading view and tells it the grades were saved', async () => {
    renderResponses({ responses: [response('learner-1', 'prompt-1', ADA_WORK_1)] });
    LessonResponseResource.grade.mockResolvedValue();
    const { frame, sent } = await openGrader();
    fromGrader(frame, {
      type: 'save-grades',
      requestId: 3,
      grades: { 'learner-1': { 'prompt-1': ADA_GRADED_1 } },
    });

    await waitFor(() =>
      expect(sent).toHaveBeenCalledWith(
        { source: 'free-math-host', type: 'save-grades-result', requestId: 3, ok: true },
        window.location.origin,
      ),
    );
    expect(LessonResponseResource.grade).toHaveBeenCalledWith({
      lessonId: 'lesson-id',
      itemId: 'contentnode-id',
      grades: { 'learner-1': { 'prompt-1': ADA_GRADED_1 } },
    });
  });

  it('tells the grading view when grades could not be saved', async () => {
    renderResponses({ responses: [response('learner-1', 'prompt-1', ADA_WORK_1)] });
    LessonResponseResource.grade.mockRejectedValue(new Error('Network error'));
    const { frame, sent } = await openGrader();
    fromGrader(frame, {
      type: 'save-grades',
      requestId: 4,
      grades: { 'learner-1': { 'prompt-1': ADA_GRADED_1 } },
    });

    await waitFor(() =>
      expect(sent).toHaveBeenCalledWith(
        { source: 'free-math-host', type: 'save-grades-result', requestId: 4, ok: false },
        window.location.origin,
      ),
    );
  });

  it('says so when no learner has answered yet', async () => {
    renderResponses();

    expect(await screen.findByTestId('no-answers')).toHaveTextContent(noAnswersYetStatus$());
    expect(screen.queryByTitle(gradingEditorLabel$())).not.toBeInTheDocument();
  });

  it('shows an error when the answers fail to load', async () => {
    LessonResource.retrieve.mockResolvedValue(LESSON);
    LessonResponseResource.list.mockRejectedValue(new Error('Network error'));
    render(LessonResourceResponses, {
      props: { lessonId: 'lesson-id', contentId: 'content-id', learners: LEARNERS },
    });

    expect(await screen.findByRole('alert')).toHaveTextContent(learnerAnswersLoadError$());
  });

  it('shows nothing for a resource without questions', async () => {
    LessonResource.retrieve.mockResolvedValue({
      title: 'Photosynthesis',
      resources: [{ ...RESOURCE, prompts: [] }],
    });
    render(LessonResourceResponses, {
      props: { lessonId: 'lesson-id', contentId: 'content-id', learners: LEARNERS },
    });
    // Let the lesson request settle
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(LessonResource.retrieve).toHaveBeenCalledWith('lesson-id');
    expect(screen.queryByRole('heading', { name: learnerAnswersLabel$() })).not.toBeInTheDocument();
    expect(LessonResponseResource.list).not.toHaveBeenCalled();
  });
});
