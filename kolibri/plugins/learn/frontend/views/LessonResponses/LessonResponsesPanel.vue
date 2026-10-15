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

      <div
        v-if="feedback && feedback.comment"
        class="feedback"
        data-testid="overall-feedback"
      >
        <h3 class="feedback-heading">
          {{ coachFeedbackLabel$() }}
        </h3>
        <p>
          <span class="multiline-text">{{ feedback.comment }}</span>
        </p>
      </div>

      <ol class="prompts">
        <li
          v-for="(prompt, index) in prompts"
          :key="prompt.id"
          class="prompt"
        >
          <h3 class="prompt-heading">
            {{ questionNumberLabel$({ number: index + 1 }) }}
          </h3>
          <p>
            <span class="multiline-text">{{ prompt.text }}</span>
          </p>

          <KTextbox
            v-if="!submitted"
            :value="answers[prompt.id] || ''"
            :label="answerToQuestionLabel$({ number: index + 1 })"
            :textArea="true"
            :maxlength="MAX_ANSWER_LENGTH"
            @input="text => setAnswer(prompt.id, text)"
            @blur="saveNow"
          />
          <p
            v-else
            class="answer"
            :data-testid="`answer-${prompt.id}`"
          >
            <span class="multiline-text">{{ answers[prompt.id] || noAnswerLabel$() }}</span>
          </p>

          <div
            v-if="promptFeedback(prompt)"
            class="feedback"
            :data-testid="`feedback-${prompt.id}`"
          >
            <h4 class="feedback-heading">
              {{ coachFeedbackLabel$() }}
            </h4>
            <p>
              <span class="multiline-text">{{ promptFeedback(prompt) }}</span>
            </p>
          </div>
        </li>
      </ol>

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

  import { computed, getCurrentInstance, ref } from 'vue';
  import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
  import useLessonResponses from '../../composables/useLessonResponses';

  // Matches the server's limit on the length of an answer
  const MAX_ANSWER_LENGTH = 10000;

  export default {
    name: 'LessonResponsesPanel',
    setup(props) {
      const {
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
      } = useLessonResponses(props.lessonId, props.contentnodeId);

      const showSubmitModal = ref(false);
      const headingId = `lesson-responses-${getCurrentInstance().uid}`;

      const answeredCount = computed(
        () => props.prompts.filter(prompt => (answers.value[prompt.id] || '').trim()).length,
      );
      const unansweredCount = computed(() => props.prompts.length - answeredCount.value);

      const {
        answerToQuestionLabel$,
        coachFeedbackLabel$,
        loadErrorStatus$,
        noAnswerLabel$,
        questionNumberLabel$,
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

      function promptFeedback(prompt) {
        return feedback.value?.prompt_comments?.[prompt.id] || '';
      }

      async function handleSubmit() {
        showSubmitModal.value = false;
        await submit();
      }

      return {
        MAX_ANSWER_LENGTH,
        answers,
        answeredCount,
        feedback,
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
        promptFeedback,
        saveNow,
        setAnswer,
        answerToQuestionLabel$,
        cancelAction$,
        coachFeedbackLabel$,
        loadErrorStatus$,
        noAnswerLabel$,
        questionNumberLabel$,
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
      contentnodeId: {
        type: String,
        required: true,
      },
      // Array of {id, text}
      prompts: {
        type: Array,
        required: true,
      },
    },
  };

</script>


<style lang="scss" scoped>

  .lesson-responses-panel {
    padding: 16px;
    background-color: var(--tokens-surface);
  }

  .heading {
    margin-top: 0;
  }

  .prompts {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .prompt {
    padding: 16px 0;
    border-top: 1px solid var(--tokens-fineLine);
  }

  .prompt-heading {
    margin: 0 0 8px;
    font-size: 16px;
  }

  .multiline-text {
    white-space: pre-wrap;
  }

  .answer {
    padding: 8px;
    background-color: var(--palette-grey-v100);
  }

  .status {
    font-weight: bold;
  }

  .feedback {
    padding: 8px 12px;
    margin-top: 8px;
    border-left: 4px solid var(--tokens-primary);
  }

  .feedback-heading {
    margin: 0;
    font-size: 14px;
  }

  .footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    padding-top: 16px;
    border-top: 1px solid var(--tokens-fineLine);

    > * {
      margin-left: 16px;
    }
  }

  .save-status {
    margin-right: auto;
    color: var(--tokens-annotation);
  }

</style>
