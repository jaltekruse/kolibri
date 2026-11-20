import { render, screen } from '@testing-library/vue';
import userEvent from '@testing-library/user-event';
import urls from 'kolibri/urls';
import redirectBrowser from 'kolibri/utils/redirectBrowser';
import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
import { quickAssignStrings } from 'kolibri-common/strings/quickAssignStrings';
import { JoinLinkResource } from '../../apiResources';
import JoinPage from '../JoinPage';

jest.mock('../../apiResources');
jest.mock('kolibri/urls');
jest.mock('kolibri/utils/redirectBrowser');

const {
  continueAsAction$,
  joinError$,
  linkClosedMessage$,
  linkNotWorkingMessage$,
  notYouAction$,
  quickAssignAction$,
  startAction$,
} = quickAssignStrings;
const { fullNameLabel$, requiredFieldError$ } = coreStrings;

const TOKEN = 'link-token';
const LEARN = '/kolibri:kolibri.plugins.learn:learn';
const LINK = {
  title: 'Two-step equations',
  coach_name: 'Ana Rivera',
  is_open: true,
  learner: null,
  is_coach: false,
};
const EXERCISE = {
  classroom_id: 'class-id',
  lesson_id: 'lesson-id',
  web_page_id: null,
  contentnode_id: 'exercise-id',
};

async function renderPage(link = LINK) {
  if (link) {
    JoinLinkResource.retrieve.mockResolvedValue(link);
  } else {
    JoinLinkResource.retrieve.mockRejectedValue({ response: { status: 404 } });
  }
  render(JoinPage, { props: { token: TOKEN } });
  await global.flushPromises();
}

describe('JoinPage', () => {
  beforeEach(() => {
    urls.__echoUrls();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('joins someone new by their name, then opens the exercise', async () => {
    JoinLinkResource.join.mockResolvedValue(EXERCISE);
    await renderPage();

    await userEvent.type(
      screen.getByRole('textbox', { name: fullNameLabel$() }),
      '  Ada Lovelace ',
    );
    await userEvent.click(screen.getByRole('button', { name: startAction$() }));

    expect(screen.queryByText(requiredFieldError$())).not.toBeInTheDocument();
    expect(JoinLinkResource.join).toHaveBeenCalledWith(TOKEN, 'Ada Lovelace');
    const prevParams = encodeURI(JSON.stringify({ classId: 'class-id', lessonId: 'lesson-id' }));
    expect(redirectBrowser).toHaveBeenCalledWith(
      `${LEARN}#/topics/c/exercise-id?${new URLSearchParams({
        prevName: 'LESSON_PLAYLIST',
        prevParams,
      })}`,
    );
  });

  it('needs a name to start', async () => {
    await renderPage();

    await userEvent.click(screen.getByRole('button', { name: startAction$() }));

    expect(JoinLinkResource.join).not.toHaveBeenCalled();
    expect(screen.getByText(requiredFieldError$())).toBeInTheDocument();
  });

  it('lets a student who joined from this browser continue, to the web page', async () => {
    JoinLinkResource.join.mockResolvedValue({
      ...EXERCISE,
      contentnode_id: null,
      web_page_id: 'web-page-id',
    });
    await renderPage({ ...LINK, learner: { full_name: 'Ada Lovelace', is_signed_in: false } });

    expect(screen.queryByRole('textbox', { name: fullNameLabel$() })).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole('button', { name: continueAsAction$({ name: 'Ada Lovelace' }) }),
    );

    expect(JoinLinkResource.join).toHaveBeenCalledWith(TOKEN, undefined);
    expect(redirectBrowser).toHaveBeenCalledWith(
      `${LEARN}#/classes/class-id/lesson/lesson-id/webpage/web-page-id`,
    );
  });

  it('lets someone else on a shared computer join as themselves', async () => {
    await renderPage({ ...LINK, learner: { full_name: 'Ada Lovelace', is_signed_in: false } });

    await userEvent.click(
      screen.getByRole('button', { name: notYouAction$({ name: 'Ada Lovelace' }) }),
    );

    expect(screen.getByRole('textbox', { name: fullNameLabel$() })).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: continueAsAction$({ name: 'Ada Lovelace' }) }),
    ).not.toBeInTheDocument();
  });

  it('tells new students when the coach stopped new students joining', async () => {
    await renderPage({ ...LINK, is_open: false });

    expect(screen.getByTestId('link-closed')).toHaveTextContent(linkClosedMessage$());
    expect(screen.queryByRole('textbox', { name: fullNameLabel$() })).not.toBeInTheDocument();
  });

  it('says so when the link closed while joining', async () => {
    JoinLinkResource.join.mockRejectedValue({ response: { status: 403 } });
    await renderPage();

    await userEvent.type(screen.getByRole('textbox', { name: fullNameLabel$() }), 'Ada');
    await userEvent.click(screen.getByRole('button', { name: startAction$() }));

    expect(await screen.findByRole('alert')).toHaveTextContent(linkClosedMessage$());
    expect(redirectBrowser).not.toHaveBeenCalled();
  });

  it('asks to try again when joining fails', async () => {
    JoinLinkResource.join.mockRejectedValue({ response: { status: 500 } });
    await renderPage();

    await userEvent.type(screen.getByRole('textbox', { name: fullNameLabel$() }), 'Ada');
    await userEvent.click(screen.getByRole('button', { name: startAction$() }));

    expect(await screen.findByRole('alert')).toHaveTextContent(joinError$());
    expect(screen.getByRole('button', { name: startAction$() })).toBeEnabled();
  });

  it('sends the coach who opens their own link back to quick assign', async () => {
    await renderPage({ ...LINK, is_coach: true });

    expect(screen.getByRole('link', { name: quickAssignAction$() })).toHaveAttribute(
      'href',
      '/kolibri:kolibri.plugins.coach:coach#/quick-assign',
    );
    expect(screen.queryByRole('textbox', { name: fullNameLabel$() })).not.toBeInTheDocument();
  });

  it('explains a link that does not work', async () => {
    await renderPage(null);

    expect(await screen.findByRole('alert')).toHaveTextContent(linkNotWorkingMessage$());
  });
});
