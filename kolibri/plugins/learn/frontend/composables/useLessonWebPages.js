import { ref, watch } from 'vue';
import LessonWebPageResource from 'kolibri-common/apiResources/LessonWebPageResource';

/**
 * The pages from the web in a lesson, which learners work from in the math editor.
 * @param {function(): string} getLessonId - Returns the lesson's id
 * @returns {{webPages: import('vue').Ref<object[]>}} The lesson's web pages, empty until
 * they load, or if they fail to load
 */
export default function useLessonWebPages(getLessonId) {
  const webPages = ref([]);

  watch(
    getLessonId,
    async lessonId => {
      webPages.value = [];
      if (!lessonId) {
        return;
      }
      try {
        const loaded = await LessonWebPageResource.list({ lesson: lessonId });
        // Ignore the response if the learner has moved on to another lesson
        if (lessonId === getLessonId()) {
          webPages.value = loaded;
        }
      } catch (error) {
        // The rest of the lesson still works without its web pages
      }
    },
    { immediate: true },
  );

  return { webPages };
}
