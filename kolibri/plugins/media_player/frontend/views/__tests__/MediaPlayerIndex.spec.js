import { render, screen } from '@testing-library/vue';
import { nextTick } from 'vue';

// video.js is the hard boundary for playing from Kolibri; useContentViewer is the
// content-data boundary. The YouTube player page is reached only through
// postMessage, so the specs send the messages it would.
jest.mock('video.js', () => require('../../test/videojsMock').videojsModuleMock());
jest.mock('kolibri/composables/useContentViewer');
jest.mock('kolibri-plugin-data', () => ({}));
jest.mock('kolibri-design-system/lib/composables/useKResponsiveElement', () => () => ({
  elementWidth: require('vue').ref(800),
}));

/* eslint-disable import-x/first, import-x/named */
import plugin_data from 'kolibri-plugin-data';
import useContentViewer, { useContentViewerMock } from 'kolibri/composables/useContentViewer';
import MediaPlayerIndex from '../MediaPlayerIndex';
import mediaStrings from '../../utils/mediaStrings';
/* eslint-enable import-x/first, import-x/named */

const PLAYER_PATH = '/content/static/youtube/player.html';
const YOUTUBE_ID = '5a6zpfl50go';
const VIDEO_FILES = [
  { storage_url: '/video.mp4', preset: 'high_res_video', extension: 'mp4', available: true },
];

function mockContent(overrides = {}) {
  useContentViewer.mockImplementation(() =>
    useContentViewerMock({
      files: VIDEO_FILES,
      defaultFile: VIDEO_FILES[0],
      options: { youtube_id: YOUTUBE_ID },
      duration: 100,
      ...overrides,
    }),
  );
}

function renderPlayer() {
  const listeners = {
    addProgress: jest.fn(),
    updateProgress: jest.fn(),
    updateContentState: jest.fn(),
    startTracking: jest.fn(),
    stopTracking: jest.fn(),
    finished: jest.fn(),
  };
  const utils = render(MediaPlayerIndex, { listeners });
  return { ...utils, listeners };
}

function youtubeFrame() {
  return screen.queryByTitle(mediaStrings.youtubeVideo$());
}

function localVideo(container) {
  return container.querySelector('video');
}

// What the YouTube player page sends: a second of wall-clock time passes before each
async function sendFromFrame(event, { currentTime = 0, duration = 100 } = {}) {
  jest.advanceTimersByTime(1000);
  const frame = youtubeFrame();
  window.dispatchEvent(
    new MessageEvent('message', {
      data: { type: 'kolibri-youtube-player', event, currentTime, duration, playbackRate: 1 },
      origin: new URL(frame.src).origin,
      source: frame.contentWindow,
    }),
  );
  await nextTick();
}

async function play(listeners, from, to, { duration = 100 } = {}) {
  await sendFromFrame('play', { currentTime: from, duration });
  for (let time = from + 1; time <= to; time++) {
    await sendFromFrame('time', { currentTime: time, duration });
  }
}

function totalProgress(listeners) {
  return listeners.addProgress.mock.calls.reduce((total, [delta]) => total + delta, 0);
}

describe('MediaPlayerIndex playing from YouTube', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    window.sessionStorage.clear();
    plugin_data.youtubePlayerUrl = PLAYER_PATH;
    mockContent();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('plays a video with a YouTube id from YouTube, not from Kolibri', () => {
    const { container } = renderPlayer();

    const src = new URL(youtubeFrame().src);
    expect(src.pathname).toBe(PLAYER_PATH);
    expect(src.searchParams.get('v')).toBe(YOUTUBE_ID);
    expect(src.searchParams.get('origin')).toBe(window.location.origin);
    expect(localVideo(container)).toBeNull();
  });

  it('plays from Kolibri when YouTube playback is off', () => {
    delete plugin_data.youtubePlayerUrl;

    const { container } = renderPlayer();

    expect(youtubeFrame()).toBeNull();
    expect(localVideo(container)).not.toBeNull();
  });

  it('plays from Kolibri when the video has no YouTube id', () => {
    mockContent({ options: {} });

    const { container } = renderPlayer();

    expect(youtubeFrame()).toBeNull();
    expect(localVideo(container)).not.toBeNull();
  });

  it('starts where the learner left off', () => {
    mockContent({ extraFields: { contentState: { savedLocation: 42 } } });

    renderPlayer();

    expect(new URL(youtubeFrame().src).searchParams.get('start')).toBe('42');
  });

  it('starts from the beginning when the learner had watched to the end', () => {
    mockContent({ extraFields: { contentState: { savedLocation: 100 } } });

    renderPlayer();

    expect(new URL(youtubeFrame().src).searchParams.get('start')).toBe('0');
  });

  it('counts the time played as progress', async () => {
    const { listeners } = renderPlayer();
    await sendFromFrame('ready');

    await play(listeners, 0, 10);
    await sendFromFrame('pause', { currentTime: 10 });

    expect(listeners.startTracking).toHaveBeenCalled();
    expect(listeners.stopTracking).toHaveBeenCalled();
    expect(totalProgress(listeners)).toBeCloseTo(0.1);
    expect(listeners.updateContentState).toHaveBeenLastCalledWith({ savedLocation: 10 });
  });

  it('does not count skipping ahead as progress', async () => {
    const { listeners } = renderPlayer();
    await sendFromFrame('ready');

    await play(listeners, 0, 10);
    await play(listeners, 80, 85);
    await sendFromFrame('pause', { currentTime: 85 });

    expect(totalProgress(listeners)).toBeCloseTo(0.15);
  });

  it('waits for YouTube to know the duration before counting progress', async () => {
    mockContent({ duration: null });
    const { listeners } = renderPlayer();
    await sendFromFrame('ready', { duration: 0 });

    await play(listeners, 0, 3, { duration: 0 });
    await play(listeners, 4, 10);
    await sendFromFrame('pause', { currentTime: 10 });

    listeners.addProgress.mock.calls.forEach(([delta]) => expect(delta).not.toBeNaN());
    expect(totalProgress(listeners)).toBeCloseTo(0.06);
  });

  it('finishes when the video ends', async () => {
    const { listeners } = renderPlayer();
    await sendFromFrame('ready');

    await sendFromFrame('ended', { currentTime: 100 });

    expect(listeners.finished).toHaveBeenCalled();
  });

  it('ignores messages from other windows', async () => {
    const { listeners } = renderPlayer();
    await sendFromFrame('ready');

    window.dispatchEvent(
      new MessageEvent('message', {
        data: { type: 'kolibri-youtube-player', event: 'ended', currentTime: 100, duration: 100 },
        origin: new URL(youtubeFrame().src).origin,
        source: window,
      }),
    );
    await nextTick();

    expect(listeners.finished).not.toHaveBeenCalled();
  });

  it('saves where the learner is when they leave', async () => {
    const { listeners, unmount } = renderPlayer();
    await sendFromFrame('ready');
    await play(listeners, 0, 7);

    unmount();

    expect(listeners.updateContentState).toHaveBeenLastCalledWith({ savedLocation: 7 });
    expect(listeners.stopTracking).toHaveBeenCalled();
  });

  it('plays from Kolibri when YouTube cannot play the video', async () => {
    const { container } = renderPlayer();

    await sendFromFrame('unplayable');

    expect(youtubeFrame()).toBeNull();
    expect(localVideo(container)).not.toBeNull();
  });

  it('plays from Kolibri, now and for later videos, when YouTube cannot be reached', async () => {
    const { container, unmount } = renderPlayer();

    await sendFromFrame('unreachable');

    expect(youtubeFrame()).toBeNull();
    expect(localVideo(container)).not.toBeNull();
    unmount();
    const next = renderPlayer();
    expect(youtubeFrame()).toBeNull();
    expect(localVideo(next.container)).not.toBeNull();
  });

  it("tries YouTube for a video that isn't on the device, though YouTube couldn't be reached before", async () => {
    const earlier = renderPlayer();
    await sendFromFrame('unreachable');
    earlier.unmount();
    mockContent({ files: [{ ...VIDEO_FILES[0], available: false }], defaultFile: undefined });

    renderPlayer();

    expect(new URL(youtubeFrame().src).searchParams.get('v')).toBe(YOUTUBE_ID);
  });

  it("says so when a video imported to play from YouTube can't", async () => {
    mockContent({ files: [{ ...VIDEO_FILES[0], available: false }], defaultFile: undefined });
    const { container } = renderPlayer();

    await sendFromFrame('unreachable');

    expect(screen.getByRole('alert')).toHaveTextContent(mediaStrings.notOnDevice$());
    expect(localVideo(container)).toBeNull();
  });

  it("says so when a video that isn't on the device has no YouTube id", () => {
    mockContent({ options: {}, defaultFile: undefined });

    const { container } = renderPlayer();

    expect(screen.getByRole('alert')).toHaveTextContent(mediaStrings.notOnDevice$());
    expect(youtubeFrame()).toBeNull();
    expect(localVideo(container)).toBeNull();
  });

  it('plays from Kolibri when YouTube takes too long to get ready', async () => {
    const { container } = renderPlayer();

    jest.advanceTimersByTime(10000);
    await nextTick();

    expect(youtubeFrame()).toBeNull();
    expect(localVideo(container)).not.toBeNull();
  });
});
