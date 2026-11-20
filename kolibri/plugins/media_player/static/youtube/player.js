/*
 * Plays a video from YouTube for Kolibri's media player. The media player frames
 * this page from the content origin, so YouTube's scripts never run on Kolibri's
 * own origin, and this page tells it, with postMessage, how the video is playing:
 *
 *   ready        the video can play
 *   play         it started playing
 *   time         it is still playing, sent every second
 *   pause        it paused
 *   ended        it played to the end
 *   unreachable  YouTube could not be reached
 *   unplayable   YouTube cannot play this video, as when its owner forbids embedding
 *
 * Each message also has the position and duration of the video, in seconds, and the
 * playback rate. The page takes its settings from its query string:
 *
 *   v         the YouTube id of the video
 *   origin    the origin of the media player, which messages are sent to
 *   start     where to start playing, in seconds
 *   autoplay  1 to start playing when ready
 *   hl        the language for YouTube's controls and captions
 */
(function () {
  var params = new URLSearchParams(window.location.search);
  var parentOrigin = params.get('origin');
  var player;
  var timer;

  function send(event) {
    var message = { type: 'kolibri-youtube-player', event: event };
    if (player && player.getCurrentTime) {
      message.currentTime = player.getCurrentTime();
      message.duration = player.getDuration();
      message.playbackRate = player.getPlaybackRate();
    }
    window.parent.postMessage(message, parentOrigin);
  }

  function stopTimer() {
    clearInterval(timer);
    timer = null;
  }

  function onStateChange(event) {
    var states = window.YT.PlayerState;
    if (event.data === states.PLAYING) {
      send('play');
      stopTimer();
      timer = setInterval(function () {
        send('time');
      }, 1000);
    } else if (event.data === states.PAUSED) {
      stopTimer();
      send('pause');
    } else if (event.data === states.ENDED) {
      stopTimer();
      send('ended');
    }
  }

  window.onYouTubeIframeAPIReady = function () {
    var language = params.get('hl') || '';
    player = new window.YT.Player('player', {
      host: 'https://www.youtube-nocookie.com',
      videoId: params.get('v'),
      width: '100%',
      height: '100%',
      playerVars: {
        autoplay: params.get('autoplay') === '1' ? 1 : 0,
        start: Math.floor(Number(params.get('start')) || 0),
        hl: language,
        cc_lang_pref: language,
        playsinline: 1,
        rel: 0,
        origin: window.location.origin,
      },
      events: {
        onReady: function () {
          send('ready');
        },
        onStateChange: onStateChange,
        onError: function () {
          stopTimer();
          send('unplayable');
        },
      },
    });
  };

  var script = document.createElement('script');
  script.src = 'https://www.youtube.com/iframe_api';
  script.onerror = function () {
    send('unreachable');
  };
  document.head.appendChild(script);
})();
