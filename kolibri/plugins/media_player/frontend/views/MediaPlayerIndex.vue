<template>

  <div>
    <YouTubePlayer
      v-if="youtubeId"
      :key="youtubeId"
      :youtubeId="youtubeId"
      v-on="$listeners"
      @unavailable="youtubeUnavailable = true"
    />
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
  import VideoPlayer from './VideoPlayer';
  import AudioPlayer from './AudioPlayer';
  import YouTubePlayer from './YouTubePlayer';

  export default {
    name: 'MediaPlayerIndex',
    components: { VideoPlayer, AudioPlayer, YouTubePlayer },
    setup(props, context) {
      const { files, options } = useContentViewer(context, { customExtractors });

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
        return playableYouTubeId(options.value);
      });

      return { isVideo, youtubeId, youtubeUnavailable };
    },
  };

</script>
