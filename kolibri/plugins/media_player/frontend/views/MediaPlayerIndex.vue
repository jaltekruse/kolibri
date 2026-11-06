<template>

  <div>
    <YouTubePlayer
      v-if="youtubeId"
      :key="youtubeId"
      :youtubeId="youtubeId"
      v-on="$listeners"
      @unavailable="youtubeUnavailable = true"
    />
    <p
      v-else-if="isVideo && !defaultFile"
      class="not-on-device"
      role="alert"
    >
      {{ notOnDevice$() }}
    </p>
    <VideoPlayer
      v-else-if="isVideo"
      v-on="$listeners"
    />
    <AudioPlayer
      v-else
      v-on="$listeners"
    />
  </div>

</template>


<script>

  import { computed, ref, watch } from 'vue';
  import useContentViewer from 'kolibri/composables/useContentViewer';
  import customExtractors, { VIDEO_PRESETS } from '../utils/fileExtractors';
  import { playableYouTubeId } from '../utils/youtube';
  import mediaStrings from '../utils/mediaStrings';
  import VideoPlayer from './VideoPlayer';
  import AudioPlayer from './AudioPlayer';
  import YouTubePlayer from './YouTubePlayer';

  export default {
    name: 'MediaPlayerIndex',
    components: { VideoPlayer, AudioPlayer, YouTubePlayer },
    setup(props, context) {
      const { files, defaultFile, options } = useContentViewer(context, { customExtractors });

      const isVideo = computed(() => {
        return files.value.some(file => VIDEO_PRESETS.has(file.preset));
      });

      // Set when YouTube cannot play this video, which then plays from Kolibri
      const youtubeUnavailable = ref(false);
      watch(
        () => options.value.youtube_id,
        () => {
          youtubeUnavailable.value = false;
        },
      );

      const youtubeId = computed(() => {
        if (!isVideo.value || youtubeUnavailable.value) {
          return null;
        }
        return playableYouTubeId(options.value, Boolean(defaultFile.value));
      });

      return {
        isVideo,
        defaultFile,
        youtubeId,
        youtubeUnavailable,
        notOnDevice$: mediaStrings.notOnDevice$,
      };
    },
  };

</script>


<style lang="scss" scoped>

  .not-on-device {
    padding: 16px;
    margin: 0;
    color: var(--tokens-text);
    background-color: var(--tokens-surface);
  }

</style>
