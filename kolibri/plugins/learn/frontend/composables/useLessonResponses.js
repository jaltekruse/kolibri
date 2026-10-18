import debounce from 'lodash/debounce';
import { computed, onBeforeUnmount, ref } from 'vue';
import LessonResponseResource from 'kolibri-common/apiResources/LessonResponseResource';

export const AUTOSAVE_DELAY = 1000;

/**
 * The current learner's answers to the prompts on a lesson resource. Each answer is
 * a Free Math document, which also holds the coach's grading once they have graded it.
 * Answers are saved automatically as the learner works, until they are submitted.
 * @param {string} lessonId - The lesson the resource is in
 * @param {string} contentnodeId - The resource the prompts are about
 * @returns {object} The answers and save state, and functions to change answers,
 * save them now, submit them, and reload them
 */
export default function useLessonResponses(lessonId, contentnodeId) {
  const params = { lesson_id: lessonId, contentnode_id: contentnodeId };

  // Base64 encoded Free Math documents keyed by prompt id
  const answers = ref({});
  // Prompt ids whose answers have changed since they were last sent
  const unsavedPromptIds = ref(new Set());
  const submitted = ref(false);
  const loading = ref(true);
  const loadError = ref(null);
  const saving = ref(false);
  const saveError = ref(null);

  const hasUnsavedAnswers = computed(() => unsavedPromptIds.value.size > 0);

  async function load() {
    loading.value = true;
    loadError.value = null;
    try {
      const responses = await LessonResponseResource.list(params);
      answers.value = Object.fromEntries(
        responses.map(response => [response.item, response.answer.free_math]),
      );
      submitted.value = responses.some(response => response.complete);
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
    const unsent = new Set(promptIds);
    try {
      // One answer per request, as answers with pictures in them can be large
      for (const promptId of promptIds) {
        await LessonResponseResource.saveAnswers({
          lessonId,
          contentnodeId,
          answers: { [promptId]: answers.value[promptId] },
        });
        unsent.delete(promptId);
      }
      if (submit) {
        await LessonResponseResource.saveAnswers({
          lessonId,
          contentnodeId,
          answers: {},
          submit,
        });
        submitted.value = true;
      }
      saveError.value = null;
    } catch (error) {
      // Send these answers again with the next save
      unsavedPromptIds.value = new Set([...unsent, ...unsavedPromptIds.value]);
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

  /**
   * Change some of the learner's answers, and save them shortly after.
   * @param {{[promptId: string]: string}} changedAnswers - Free Math documents keyed by
   * prompt id
   */
  function setAnswers(changedAnswers) {
    if (submitted.value || loadError.value) {
      return;
    }
    answers.value = { ...answers.value, ...changedAnswers };
    unsavedPromptIds.value = new Set([...unsavedPromptIds.value, ...Object.keys(changedAnswers)]);
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
    hasUnsavedAnswers,
    loadError,
    loading,
    saveError,
    saving,
    submitted,
    load,
    saveNow,
    setAnswers,
    submit,
  };
}
