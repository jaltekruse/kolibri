import { render, screen } from '@testing-library/vue';
import VueRouter from 'vue-router';
import LessonResponseResource from 'kolibri-common/apiResources/LessonResponseResource';
import LessonWebPageResource from 'kolibri-common/apiResources/LessonWebPageResource';
import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
import { ClassesPageNames } from '../../../constants';
import LessonWebPagePage from '../LessonWebPagePage';

jest.mock('kolibri-common/apiResources/LessonResponseResource');
jest.mock('kolibri-common/apiResources/LessonWebPageResource');
jest.mock('kolibri/composables/useUser');
// The editor's page URL
jest.mock('kolibri/urls');

const { mathEditorLabel$, openWebPageAction$, webPagesLoadError$ } = lessonResponsesStrings;

const WEB_PAGE = {
  id: 'web-page-id',
  lesson: 'lesson-id',
  title: 'Two-step equations',
  url: 'https://example.org/equations',
  instructions: 'Solve every third problem',
  problem_numbers: '21-27 by 3',
  problems: ['21', '24', '27'],
};

async function renderPage() {
  const router = new VueRouter({
    routes: [
      { name: ClassesPageNames.LESSON_PLAYLIST, path: '/classes/:classId/lesson/:lessonId' },
      {
        name: ClassesPageNames.LESSON_WEB_PAGE,
        path: '/classes/:classId/lesson/:lessonId/webpage/:webPageId',
        component: LessonWebPagePage,
      },
    ],
  });
  await router.push({
    name: ClassesPageNames.LESSON_WEB_PAGE,
    params: { classId: 'class-id', lessonId: 'lesson-id', webPageId: WEB_PAGE.id },
  });
  return render({ template: '<router-view />' }, { routes: router });
}

describe('LessonWebPagePage', () => {
  beforeEach(() => {
    LessonResponseResource.list.mockResolvedValue([]);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('shows the web page in a frame that cannot navigate Kolibri, with a link to open it', async () => {
    LessonWebPageResource.retrieve.mockResolvedValue(WEB_PAGE);
    await renderPage();

    const frame = await screen.findByTitle(WEB_PAGE.title);
    expect(frame).toHaveAttribute('src', WEB_PAGE.url);
    expect(frame.getAttribute('sandbox')).not.toContain('allow-top-navigation');
    expect(frame).toHaveAttribute('referrerpolicy', 'no-referrer');
    expect(screen.getByRole('link', { name: openWebPageAction$() })).toHaveAttribute(
      'href',
      WEB_PAGE.url,
    );
    expect(LessonWebPageResource.retrieve).toHaveBeenCalledWith(WEB_PAGE.id);
  });

  it('opens the listed problems in the math editor, numbered as listed', async () => {
    LessonWebPageResource.retrieve.mockResolvedValue(WEB_PAGE);
    await renderPage();

    const editor = await screen.findByTitle(mathEditorLabel$());
    const sent = jest.spyOn(editor.contentWindow, 'postMessage').mockImplementation(() => {});
    window.dispatchEvent(
      new MessageEvent('message', {
        data: { source: 'free-math', type: 'ready' },
        origin: window.location.origin,
        source: editor.contentWindow,
      }),
    );

    expect(screen.getByTestId('instructions')).toHaveTextContent(WEB_PAGE.instructions);
    expect(LessonResponseResource.list).toHaveBeenCalledWith({
      lesson_id: 'lesson-id',
      item_id: WEB_PAGE.id,
    });
    const [message] = sent.mock.calls[0];
    expect(message.problems).toEqual(
      ['21', '24', '27'].map(number => ({ key: number, number, prompt: '', content: '' })),
    );
  });

  it('shows an error when the web page fails to load', async () => {
    LessonWebPageResource.retrieve.mockRejectedValue(new Error('Not found'));
    await renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent(webPagesLoadError$());
  });
});
