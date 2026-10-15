import debounce from 'lodash/debounce';
import { computed, onBeforeUnmount, ref } from 'vue';
import LessonResponseResource from 'kolibri-common/apiResources/LessonResponseResource';
import LessonResponseFeedbackResource from 'kolibri-common/apiResources/LessonResponseFeedbackResource';

export const AUTOSAVE_DELAY = 2000;

/**
 * The current learner's answers to the prompts on a lesson resource, and their coach's
 * feedback. Answers are saved automatically as the learner types, until they are submitted.
 * @param {string} lessonId
 * @param {string} contentnodeId
 */
export default function useLessonResponses(lessonId, contentnodeId) {
  const params = { lesson_id: lessonId, contentnode_id: contentnodeId };

  // Answer text keyed by prompt id
  const answers = ref({});
  // Prompt ids whose answers have changed since they were last sent
  const unsavedPromptIds = ref(new Set());
  const submitted = ref(false);
  const feedback = ref(null);
  const loading = ref(true);
  const loadError = ref(null);
  const saving = ref(false);
  const saveError = ref(null);

  const hasUnsavedAnswers = computed(() => unsavedPromptIds.value.size > 0);

  async function load() {
    loading.value = true;
    loadError.value = null;
    try {
      const [responses, feedbackList] = await Promise.all([
        LessonResponseResource.list(params),
        LessonResponseFeedbackResource.list(params),
      ]);
      answers.value = Object.fromEntries(
        responses.map(response => [response.item, response.answer.text]),
      );
      submitted.value = responses.some(response => response.complete);
      feedback.value = feedbackList[0] || null;
    } catch (error) {
      loadError.value = error;
    } finally {
      loading.value = false;
    }
  }

  async function sendAnswers(submit) {
    // Only answers changed since the last save are sent; the server already has the rest.
    const promptIds = [...unsavedPromptIds.value];
    if (!promptIds.length && !submit) {
      return;
    }
    unsavedPromptIds.value = new Set();
    saving.value = true;
    try {
      await LessonResponseResource.saveAnswers({
        lessonId,
        contentnodeId,
        answers: Object.fromEntries(promptIds.map(id => [id, answers.value[id]])),
        submit,
      });
      saveError.value = null;
      if (submit) {
        submitted.value = true;
      }
    } catch (error) {
      // Send these answers again with the next save
      unsavedPromptIds.value = new Set([...promptIds, ...unsavedPromptIds.value]);
      saveError.value = error;
    } finally {
      saving.value = false;
    }
  }

  // Saves run one at a time, so a slow request can never overwrite a newer answer.
  let saveQueue = Promise.resolve();

  function save({ submit = false } = {}) {
    saveQueue = saveQueue.then(() => sendAnswers(submit));
    return saveQueue;
  }

  const autosave = debounce(() => save(), AUTOSAVE_DELAY);

  function setAnswer(promptId, text) {
    if (submitted.value || loadError.value) {
      return;
    }
    answers.value = { ...answers.value, [promptId]: text };
    unsavedPromptIds.value = new Set([...unsavedPromptIds.value, promptId]);
    autosave();
  }

  function saveNow() {
    autosave.cancel();
    return save();
  }

  function submit() {
    autosave.cancel();
    return save({ submit: true });
  }

  onBeforeUnmount(() => {
    autosave.flush();
  });

  load();

  return {
    answers,
    feedback,
    hasUnsavedAnswers,
    loadError,
    loading,
    saveError,
    saving,
    submitted,
    load,
    saveNow,
    setAnswer,
    submit,
  };
}
