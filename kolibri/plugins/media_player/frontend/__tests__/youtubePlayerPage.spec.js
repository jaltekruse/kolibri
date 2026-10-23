// The YouTube player page, which Kolibri serves from the content origin, run
// against a fake of YouTube's IFrame API, the boundary it talks to.
const KOLIBRI_ORIGIN = 'http://kolibri.test';
const STATES = { ENDED: 0, PLAYING: 1, PAUSED: 2 };

function fakeYouTube() {
  const player = {
    position: 0,
    getCurrentTime: () => player.position,
    getDuration: () => 100,
    getPlaybackRate: () => 1,
  };
  window.YT = {
    PlayerState: STATES,
    Player: jest.fn((elementId, config) => {
      player.config = config;
      return player;
    }),
  };
  return player;
}

function openPage(query) {
  window.history.replaceState(null, '', `/content/static/youtube/player.html?${query}`);
  document.head.innerHTML = '';
  jest.isolateModules(() => {
    require('../../static/youtube/player.js');
  });
}

function youtubeApiScript() {
  return document.head.querySelector('script[src="https://www.youtube.com/iframe_api"]');
}

function sentEvents() {
  return window.postMessage.mock.calls.map(([message, origin]) => {
    expect(origin).toBe(KOLIBRI_ORIGIN);
    expect(message.type).toBe('kolibri-youtube-player');
    return message.event;
  });
}

function lastMessage() {
  return window.postMessage.mock.calls.at(-1)[0];
}

describe('YouTube player page', () => {
  let player;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.spyOn(window, 'postMessage').mockImplementation(() => {});
    player = fakeYouTube();
    openPage(
      `v=5a6zpfl50go&origin=${encodeURIComponent(KOLIBRI_ORIGIN)}&start=42&autoplay=1&hl=es`,
    );
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
    delete window.YT;
    delete window.onYouTubeIframeAPIReady;
  });

  it('says YouTube cannot be reached when its API does not load', () => {
    youtubeApiScript().dispatchEvent(new Event('error'));

    expect(sentEvents()).toEqual(['unreachable']);
  });

  it('plays the video from youtube-nocookie.com as the query string asks', () => {
    window.onYouTubeIframeAPIReady();

    const [elementId, config] = window.YT.Player.mock.calls[0];
    expect(elementId).toBe('player');
    expect(config.host).toBe('https://www.youtube-nocookie.com');
    expect(config.videoId).toBe('5a6zpfl50go');
    expect(config.playerVars).toMatchObject({
      start: 42,
      autoplay: 1,
      hl: 'es',
      cc_lang_pref: 'es',
    });
  });

  it('tells Kolibri how the video is playing', () => {
    window.onYouTubeIframeAPIReady();
    const { events } = player.config;

    player.position = 42;
    events.onReady();
    events.onStateChange({ data: STATES.PLAYING });
    player.position = 44;
    jest.advanceTimersByTime(2000);
    events.onStateChange({ data: STATES.PAUSED });
    jest.advanceTimersByTime(5000);

    expect(sentEvents()).toEqual(['ready', 'play', 'time', 'time', 'pause']);
    expect(lastMessage()).toMatchObject({ currentTime: 44, duration: 100, playbackRate: 1 });
  });

  it('says when the video ends', () => {
    window.onYouTubeIframeAPIReady();
    const { events } = player.config;

    events.onStateChange({ data: STATES.PLAYING });
    events.onStateChange({ data: STATES.ENDED });
    jest.advanceTimersByTime(5000);

    expect(sentEvents()).toEqual(['play', 'ended']);
  });

  it('says when YouTube cannot play the video', () => {
    window.onYouTubeIframeAPIReady();

    player.config.events.onError({ data: 150 });

    expect(sentEvents()).toEqual(['unplayable']);
  });
});
