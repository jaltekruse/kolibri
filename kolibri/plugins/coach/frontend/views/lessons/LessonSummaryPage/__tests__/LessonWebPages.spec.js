import { render, screen, fireEvent, waitFor, within } from '@testing-library/vue';
import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
import LessonWebPageResource from 'kolibri-common/apiResources/LessonWebPageResource';
import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
import { coachStrings } from '../../../common/commonCoachStrings';
import { PageNames } from '../../../../constants';
import LessonWebPages from '../LessonWebPages';

jest.mock('kolibri-common/apiResources/LessonWebPageResource');
jest.mock('kolibri/composables/useSnackbar');

const {
  addWebPageAction$,
  noWebPagesDescription$,
  problemNumbersInvalid$,
  problemNumbersLabel$,
  removeWebPageTitle$,
  webPageUrlInvalid$,
  webPageUrlLabel$,
  webPagesLoadError$,
} = lessonResponsesStrings;
const { editAction$, removeAction$, saveAction$ } = coreStrings;
const { titleLabel$ } = coachStrings;

const CLASS_ID = 'class-id';
const LESSON_ID = 'lesson-id';
const NEW_TITLE = 'Fractions';
const CHANGED_TITLE = 'Equations practice';
const WEB_PAGE = {
  id: 'web-page-id',
  lesson: LESSON_ID,
  title: 'Two-step equations',
  url: 'https://example.org/equations',
  instructions: 'Solve the odd problems',
  problem_numbers: '1-5',
  problems: ['1', '2', '3', '4', '5'],
};

function renderWebPages({ webPages = [WEB_PAGE], editable = true } = {}) {
  LessonWebPageResource.list.mockResolvedValue(webPages);
  return render(LessonWebPages, {
    props: { classId: CLASS_ID, lessonId: LESSON_ID, editable },
    routes: [
      {
        name: PageNames.LESSON_WEB_PAGE_REPORT,
        path: '/:classId/lessons/:lessonId/webpages/:webPageId',
      },
    ],
  });
}

async function fillForm(dialog, { title, url, problemNumbers }) {
  await fireEvent.update(within(dialog).getByRole('textbox', { name: titleLabel$() }), title);
  await fireEvent.update(within(dialog).getByRole('textbox', { name: webPageUrlLabel$() }), url);
  await fireEvent.update(
    within(dialog).getByRole('textbox', { name: problemNumbersLabel$() }),
    problemNumbers,
  );
}

describe('LessonWebPages', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("lists the lesson's web pages, each linking to its report", async () => {
    renderWebPages();

    const link = await screen.findByRole('link', { name: WEB_PAGE.title });
    expect(link).toHaveAttribute(
      'href',
      `#/${CLASS_ID}/lessons/${LESSON_ID}/webpages/${WEB_PAGE.id}`,
    );
    expect(LessonWebPageResource.list).toHaveBeenCalledWith({ lesson: LESSON_ID });
  });

  it('adds a web page', async () => {
    const created = { ...WEB_PAGE, id: 'new-id', title: NEW_TITLE };
    LessonWebPageResource.create.mockResolvedValue(created);
    renderWebPages({ webPages: [] });
    await screen.findByTestId('no-web-pages');
    await fireEvent.click(screen.getByRole('button', { name: addWebPageAction$() }));
    const dialog = screen.getByRole('dialog');
    await fillForm(dialog, {
      title: NEW_TITLE,
      url: 'https://example.org/fractions',
      problemNumbers: '1-10, 21-35 by 3',
    });
    await fireEvent.click(within(dialog).getByRole('button', { name: saveAction$() }));

    expect(await screen.findByRole('link', { name: NEW_TITLE })).toBeInTheDocument();
    expect(LessonWebPageResource.create).toHaveBeenCalledWith({
      lesson: LESSON_ID,
      title: NEW_TITLE,
      url: 'https://example.org/fractions',
      instructions: '',
      problem_numbers: '1-10, 21-35 by 3',
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('only accepts web addresses', async () => {
    renderWebPages({ webPages: [] });
    await screen.findByTestId('no-web-pages');
    await fireEvent.click(screen.getByRole('button', { name: addWebPageAction$() }));
    const dialog = screen.getByRole('dialog');
    await fillForm(dialog, {
      title: NEW_TITLE,
      url: 'javascript:alert(1)',
      problemNumbers: '1-10',
    });
    await fireEvent.click(within(dialog).getByRole('button', { name: saveAction$() }));

    expect(dialog).toHaveTextContent(webPageUrlInvalid$());
    expect(LessonWebPageResource.create).not.toHaveBeenCalled();
  });

  it('says when the problem numbers cannot be used', async () => {
    LessonWebPageResource.create.mockRejectedValue({
      response: {
        status: 400,
        data: [{ id: 'INVALID', metadata: { field: 'problem_numbers', message: 'Invalid' } }],
      },
    });
    renderWebPages({ webPages: [] });
    await screen.findByTestId('no-web-pages');
    await fireEvent.click(screen.getByRole('button', { name: addWebPageAction$() }));
    const dialog = screen.getByRole('dialog');
    await fillForm(dialog, {
      title: NEW_TITLE,
      url: 'https://example.org/fractions',
      problemNumbers: '35-21',
    });
    await fireEvent.click(within(dialog).getByRole('button', { name: saveAction$() }));

    await waitFor(() => expect(dialog).toHaveTextContent(problemNumbersInvalid$()));
  });

  it('changes a web page', async () => {
    LessonWebPageResource.update.mockResolvedValue({ ...WEB_PAGE, title: CHANGED_TITLE });
    renderWebPages();
    const row = await screen.findByTestId(`web-page-${WEB_PAGE.id}`);
    await fireEvent.click(within(row).getByRole('button', { name: editAction$() }));
    const dialog = screen.getByRole('dialog');
    const title = within(dialog).getByRole('textbox', { name: titleLabel$() });
    expect(title).toHaveValue(WEB_PAGE.title);
    await fireEvent.update(title, CHANGED_TITLE);
    await fireEvent.click(within(dialog).getByRole('button', { name: saveAction$() }));

    expect(await screen.findByRole('link', { name: CHANGED_TITLE })).toBeInTheDocument();
    expect(LessonWebPageResource.update).toHaveBeenCalledWith(
      WEB_PAGE.id,
      expect.objectContaining({ title: CHANGED_TITLE }),
    );
  });

  it('removes a web page after the coach confirms', async () => {
    LessonWebPageResource.delete.mockResolvedValue(WEB_PAGE.id);
    renderWebPages();
    const row = await screen.findByTestId(`web-page-${WEB_PAGE.id}`);
    await fireEvent.click(within(row).getByRole('button', { name: removeAction$() }));
    const dialog = screen.getByRole('dialog', { name: removeWebPageTitle$() });
    await fireEvent.click(within(dialog).getByRole('button', { name: removeAction$() }));

    expect(await screen.findByTestId('no-web-pages')).toHaveTextContent(noWebPagesDescription$());
    expect(LessonWebPageResource.delete).toHaveBeenCalledWith(WEB_PAGE.id);
  });

  it('cannot change web pages when the lesson cannot be edited', async () => {
    renderWebPages({ editable: false });
    await screen.findByRole('link', { name: WEB_PAGE.title });

    expect(screen.queryByRole('button', { name: addWebPageAction$() })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: editAction$() })).not.toBeInTheDocument();
  });

  it('shows an error when the web pages fail to load', async () => {
    LessonWebPageResource.list.mockRejectedValue(new Error('Network error'));
    render(LessonWebPages, {
      props: { classId: CLASS_ID, lessonId: LESSON_ID },
      routes: [],
    });

    expect(await screen.findByRole('alert')).toHaveTextContent(webPagesLoadError$());
  });
});
