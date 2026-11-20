/**
 * Playing videos from YouTube. When Kolibri's YOUTUBE_PLAYBACK option is on, a
 * video whose options have a YouTube id plays from YouTube, in a page on the
 * content origin, unless YouTube cannot be reached or cannot play it.
 */
import plugin_data from 'kolibri-plugin-data';
import urls from 'kolibri/urls';

// The type of the messages the YouTube player page sends
export const YOUTUBE_PLAYER_MESSAGE = 'kolibri-youtube-player';

const YOUTUBE_ID = /^[\w-]{11}$/;

// Once YouTube cannot be reached, videos on the device play from Kolibri without
// waiting for YouTube again, for the rest of the browser session. Videos that aren't
// on the device have nothing else to play, so they still try YouTube.
const UNREACHABLE_KEY = 'kolibriYouTubeUnreachable';

export function setYouTubeUnreachable() {
  window.sessionStorage.setItem(UNREACHABLE_KEY, 'true');
}

/**
 * The YouTube id to play a video from, or null to play it from Kolibri.
 * @param {object} options - The content node's options, where a YouTube id is kept
 * @param {boolean} onDevice - Whether the video's file is on the device to play instead
 * @returns {string|null} An id that YouTube can be asked to play
 */
export function playableYouTubeId(options, onDevice) {
  const youtubeId = options && options.youtube_id;
  if (
    !plugin_data.youtubePlayerUrl ||
    (onDevice && window.sessionStorage.getItem(UNREACHABLE_KEY)) ||
    !YOUTUBE_ID.test(youtubeId)
  ) {
    return null;
  }
  return youtubeId;
}

/**
 * The URL of the YouTube player page for a video.
 * @param {object} video - The video to play
 * @param {string} video.youtubeId - Its YouTube id
 * @param {number} video.start - Where to start playing, in seconds
 * @param {boolean} video.autoplay - Whether to start playing when it is ready
 * @param {string} video.language - The language for YouTube's controls and captions
 * @returns {string} An address on the content origin, for the video's frame
 */
export function youtubePlayerUrl({ youtubeId, start, autoplay, language }) {
  const url = new URL(plugin_data.youtubePlayerUrl, urls.zipContentOrigin());
  url.search = new URLSearchParams({
    v: youtubeId,
    origin: window.location.origin,
    start: String(Math.floor(start)),
    autoplay: autoplay ? '1' : '0',
    hl: language,
  }).toString();
  return url.href;
}
