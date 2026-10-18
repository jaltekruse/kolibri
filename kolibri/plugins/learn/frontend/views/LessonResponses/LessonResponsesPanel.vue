<template>

  <section
    class="lesson-responses-panel"
    :aria-labelledby="headingId"
  >
    <h2
      :id="headingId"
      class="heading"
    >
      {{ questionsLabel$() }}
    </h2>

    <KCircularLoader v-if="loading" />

    <div
      v-else-if="loadError"
      role="alert"
    >
      <p>{{ loadErrorStatus$() }}</p>
      <KButton
        :text="tryAgainAction$()"
        appearance="flat-button"
        @click="load"
      />
    </div>

    <template v-else>
      <p
        v-if="instructions"
        class="instructions"
        data-testid="instructions"
      >
        <span class="multiline-text">{{ instructions }}</span>
      </p>
      <p
        v-if="submitted"
        class="status"
        data-testid="submitted-status"
      >
        {{ submittedStatus$() }}
      </p>
      <p
        v-else
        class="description"
      >
        {{ questionsDescription$() }}
      </p>

      <FreeMathFrame
        ref="editor"
        class="editor"
        mode="student"
        :title="mathEditorLabel$()"
        @ready="showWork"
        @save="setAnswers"
      />

      <div
        v-if="!submitted"
        class="footer"
      >
        <span
          class="save-status"
          aria-live="polite"
          data-testid="save-status"
        >
          {{ saveStatus }}
        </span>
        <KButton
          v-if="saveError"
          :text="tryAgainAction$()"
          appearance="flat-button"
          @click="saveNow"
        />
        <KButton
          :text="submitAnswersAction$()"
          :primary="true"
          :disabled="answeredCount === 0 || saving"
          @click="showSubmitModal = true"
        />
      </div>
    </template>

    <KModal
      v-if="showSubmitModal"
      :title="submitAnswersTitle$()"
      :submitText="submitAnswersAction$()"
      :cancelText="cancelAction$()"
      @submit="handleSubmit"
      @cancel="showSubmitModal = false"
    >
      <p>{{ submitAnswersDescription$() }}</p>
      <p v-if="unansweredCount > 0">
        {{ unansweredQuestionsWarning$({ count: unansweredCount }) }}
      </p>
    </KModal>
  </section>

</template>


<script>

  import { computed, getCurrentInstance, ref, watch } from 'vue';
  import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
  import FreeMathFrame from 'kolibri-common/components/FreeMathFrame';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
  import useLessonResponses from '../../composables/useLessonResponses';

  /**
   * The problems learners answer about a lesson item, by showing their work in the
   * Free Math editor: the questions a coach wrote about a lesson resource, or the
   * problems the coach listed for a web page.
   */
  export default {
    name: 'LessonResponsesPanel',
    components: {
      FreeMathFrame,
    },
    setup(props) {
      const {
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
      } = useLessonResponses(props.lessonId, props.itemId);

      const editor = ref(null);
      const showSubmitModal = ref(false);
      const headingId = `lesson-responses-${getCurrentInstance().uid}`;

      const answeredCount = computed(
        () => props.problems.filter(problem => answers.value[problem.key]).length,
      );
      const unansweredCount = computed(() => props.problems.length - answeredCount.value);

      const {
        loadErrorStatus$,
        mathEditorLabel$,
        questionsDescription$,
        questionsLabel$,
        savedStatus$,
        saveErrorStatus$,
        savingStatus$,
        submitAnswersAction$,
        submitAnswersDescription$,
        submitAnswersTitle$,
        submittedStatus$,
        tryAgainAction$,
        unansweredQuestionsWarning$,
      } = lessonResponsesStrings;
      const { cancelAction$ } = coreStrings;

      const saveStatus = computed(() => {
        if (saveError.value) {
          return saveErrorStatus$();
        }
        if (saving.value) {
          return savingStatus$();
        }
        if (!hasUnsavedAnswers.value && answeredCount.value > 0) {
          return savedStatus$();
        }
        return '';
      });

      // Send the problems, with the learner's work on them, to the editor
      function showWork() {
        editor.value.send('load-student', {
          title: props.title,
          readOnly: submitted.value,
          problems: props.problems.map(problem => ({
            ...problem,
            content: answers.value[problem.key] || '',
          })),
        });
      }

      // Submitted work can no longer be changed
      watch(submitted, isSubmitted => {
        if (isSubmitted && editor.value) {
          showWork();
        }
      });

      async function handleSubmit() {
        showSubmitModal.value = false;
        // Include the work the editor has not sent yet
        await editor.value.flush();
        await submit();
      }

      return {
        answeredCount,
        editor,
        headingId,
        loadError,
        loading,
        saveError,
        saveStatus,
        saving,
        showSubmitModal,
        submitted,
        unansweredCount,
        handleSubmit,
        load,
        saveNow,
        setAnswers,
        showWork,
        cancelAction$,
        loadErrorStatus$,
        mathEditorLabel$,
        questionsDescription$,
        questionsLabel$,
        submitAnswersAction$,
        submitAnswersDescription$,
        submitAnswersTitle$,
        submittedStatus$,
        tryAgainAction$,
        unansweredQuestionsWarning$,
      };
    },
    props: {
      lessonId: {
        type: String,
        required: true,
      },
      // A lesson resource's contentnode_id, or a lesson web page's id
      itemId: {
        type: String,
        required: true,
      },
      // Array of {key, number, prompt}: how answers are saved, the problem number
      // shown in the editor, and the question, if any
      problems: {
        type: Array,
        required: true,
      },
      // What the coach asked learners to do, if more than the problems say
      instructions: {
        type: String,
        default: '',
      },
      // Title of the lesson item, shown in the editor
      title: {
        type: String,
        default: '',
      },
    },
  };

</script>


<style lang="scss" scoped>

  .lesson-responses-panel {
    display: flex;
    flex-direction: column;
    padding: 16px;
    background-color: var(--tokens-surface);
  }

  .heading {
    margin-top: 0;
  }

  .status {
    font-weight: bold;
  }

  .multiline-text {
    white-space: pre-wrap;
  }

  .editor {
    // Fills the panel when it has a fixed height, and is this tall otherwise
    flex: 1 1 75vh;
    min-height: 400px;
    border: 1px solid var(--tokens-fineLine);
  }

  .footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    padding-top: 16px;

    > * {
      margin-left: 16px;
    }
  }

  .save-status {
    margin-right: auto;
    color: var(--tokens-annotation);
  }

</style>
