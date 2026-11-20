<template>

  <div class="youtube-player">
    <iframe
      ref="frame"
      class="frame"
      :src="src"
      :title="youtubeVideo$()"
      allow="autoplay; encrypted-media; fullscreen; picture-in-picture"
      allowfullscreen
      :sandbox="sandbox"
    ></iframe>
    <KCircularLoader
      v-if="loading"
      class="loader"
      :delay="true"
    />
  </div>

</template>


<script>

  import { computed, onBeforeUnmount, ref } from 'vue';
  import { useEventListener, useIntervalFn, useTimeoutFn } from '@vueuse/core';
  import useContentViewer from 'kolibri/composables/useContentViewer';
  import { currentLanguage } from 'kolibri/utils/i18n';
  import useMediaProgress from '../composables/useMediaProgress';
  import customExtractors from '../utils/fileExtractors';
  import mediaStrings from '../utils/mediaStrings';
  import {
    YOUTUBE_PLAYER_MESSAGE,
    setYouTubeUnreachable,
    youtubePlayerUrl,
  } from '../utils/youtube';

  // YouTube's player needs its scripts and its own origin's storage, and opens
  // youtube.com in a new tab from its logo
  const FRAME_SANDBOX = [
    'allow-scripts',
    'allow-same-origin',
    'allow-presentation',
    'allow-popups',
    'allow-popups-to-escape-sandbox',
  ].join(' ');

  // How long YouTube has to get ready before the video plays from Kolibri instead
  const READY_TIMEOUT = 10000;

  // How far, in seconds, the video can be from where playing would have taken it
  // without counting as a seek. YouTube does not say when the learner seeks.
  const SEEK_TOLERANCE = 2;

  export default {
    name: 'YouTubePlayer',
    setup(props, context) {
      const currentTime = ref(0);
      const duration = ref(0);
      const loading = ref(true);
      const frame = ref(null);

      const {
        duration: contentDuration,
        extraFields,
        embedded,
        forceDurationBasedProgress,
        durationBasedProgress,
      } = useContentViewer(context, { defaultDuration: duration, customExtractors });

      const savedLocation = computed(() => extraFields.value?.contentState?.savedLocation ?? 0);

      // Not computed: the frame must not reload as the saved location changes
      const src = youtubePlayerUrl({
        youtubeId: props.youtubeId,
        start: savedLocation.value >= (contentDuration.value || Infinity) ? 0 : savedLocation.value,
        autoplay: !embedded.value,
        language: currentLanguage,
      });
      const frameOrigin = new URL(src).origin;

      // The YouTube player in the frame, as far as useMediaProgress needs one
      const player = ref({
        currentTime: () => currentTime.value,
        duration: () => duration.value,
        seeking: () => false,
      });
      const { updateContentState, updateTime, handleSeek, setPlayState } = useMediaProgress({
        player,
        emit: context.emit,
        forceDurationBasedProgress,
        durationBasedProgress,
        extraFields,
        savedLocation,
      });

      const { pause: pauseContentStateSync, resume: resumeContentStateSync } = useIntervalFn(
        updateContentState,
        30000,
        { immediate: false },
      );

      const { stop: stopReadyTimeout } = useTimeoutFn(() => {
        setYouTubeUnreachable();
        context.emit('unavailable');
      }, READY_TIMEOUT);

      let playing = false;
      let playbackRate = 1;
      let lastMessageAt = Date.now();
      // Progress is a fraction of the duration, which YouTube may not know
      // until the video starts, so it is only tracked once the duration is known
      let tracking = false;

      function receivePosition(message) {
        const now = Date.now();
        const played = playing ? ((now - lastMessageAt) / 1000) * playbackRate : 0;
        const seeked =
          Math.abs(message.currentTime - (currentTime.value + played)) > SEEK_TOLERANCE;
        lastMessageAt = now;
        playbackRate = message.playbackRate || 1;
        currentTime.value = message.currentTime;
        duration.value = message.duration || contentDuration.value || 0;
        if (!duration.value) {
          return;
        }
        if (seeked || !tracking) {
          // Also counts nothing from before it was tracked
          handleSeek();
        } else {
          updateTime();
        }
        tracking = true;
      }

      function setPlaying(state) {
        playing = state;
        if (tracking) {
          setPlayState(state);
        } else {
          context.emit(state ? 'startTracking' : 'stopTracking');
        }
      }

      const handlers = {
        ready(message) {
          stopReadyTimeout();
          loading.value = false;
          receivePosition(message);
          resumeContentStateSync();
        },
        play(message) {
          receivePosition(message);
          setPlaying(true);
        },
        time: receivePosition,
        pause(message) {
          receivePosition(message);
          setPlaying(false);
          updateContentState();
        },
        ended(message) {
          receivePosition(message);
          setPlaying(false);
          context.emit('finished');
        },
        unreachable() {
          stopReadyTimeout();
          setYouTubeUnreachable();
          context.emit('unavailable');
        },
        unplayable() {
          stopReadyTimeout();
          context.emit('unavailable');
        },
      };

      useEventListener(window, 'message', event => {
        const message = event.data;
        if (
          event.origin !== frameOrigin ||
          !frame.value ||
          event.source !== frame.value.contentWindow ||
          message?.type !== YOUTUBE_PLAYER_MESSAGE ||
          !Object.prototype.hasOwnProperty.call(handlers, message.event)
        ) {
          return;
        }
        handlers[message.event](message);
      });

      onBeforeUnmount(() => {
        pauseContentStateSync();
        updateContentState();
        context.emit('stopTracking');
      });

      const { youtubeVideo$ } = mediaStrings;

      return {
        frame,
        loading,
        src,
        sandbox: FRAME_SANDBOX,
        youtubeVideo$,
      };
    },
    props: {
      youtubeId: {
        type: String,
        required: true,
      },
    },
  };

</script>


<style lang="scss" scoped>

  @import './videojs-style/variables';

  .youtube-player {
    position: relative;
    width: 100%;
    padding-top: $video-player-height-by-width;
  }

  .frame {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border: 0;
  }

  .loader {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
  }

</style>
