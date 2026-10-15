<template>

  <div class="learner-responses">
    <h3 class="learner-name">
      {{ learnerName }}
    </h3>
    <p
      class="status"
      data-testid="status"
    >
      {{ status }}
    </p>

    <ol
      v-if="hasAnswers"
      class="answers"
    >
      <li
        v-for="(prompt, index) in prompts"
        :key="prompt.id"
        class="answer-item"
      >
        <h4 class="question-heading">
          {{ questionNumberLabel$({ number: index + 1 }) }}
        </h4>
        <p class="question">
          <span class="multiline-text">{{ prompt.text }}</span>
        </p>
        <p
          class="answer"
          :data-testid="`answer-${prompt.id}`"
        >
          <span class="multiline-text">{{ answers[prompt.id] || noAnswerLabel$() }}</span>
        </p>

        <KTextbox
          v-if="editing"
          v-model="workingPromptComments[prompt.id]"
          :label="answerFeedbackLabel$()"
          :textArea="true"
          :maxlength="MAX_COMMENT_LENGTH"
        />
        <p
          v-else-if="promptComment(prompt)"
          class="feedback"
          :data-testid="`feedback-${prompt.id}`"
        >
          <span class="multiline-text">{{ promptComment(prompt) }}</span>
        </p>
      </li>
    </ol>

    <template v-if="editing">
      <KTextbox
        v-model="workingComment"
        :label="overallFeedbackLabel$()"
        :textArea="true"
        :maxlength="MAX_COMMENT_LENGTH"
      />
      <KButtonGroup>
        <KButton
          :text="cancelAction$()"
          @click="editing = false"
        />
        <KButton
          :text="saveAction$()"
          :primary="true"
          :disabled="saving"
          @click="saveFeedback"
        />
      </KButtonGroup>
    </template>
    <template v-else-if="hasAnswers">
      <div
        v-if="feedback && feedback.comment"
        class="feedback"
        data-testid="overall-feedback"
      >
        <h4 class="feedback-heading">
          {{ feedbackLabel$() }}
        </h4>
        <p>
          <span class="multiline-text">{{ feedback.comment }}</span>
        </p>
      </div>
      <KButton
        appearance="flat-button"
        :text="feedback ? editFeedbackAction$() : addFeedbackAction$()"
        @click="startEditing"
      />
    </template>
  </div>

</template>


<script>

  import { computed, ref } from 'vue';
  import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
  import useSnackbar from 'kolibri/composables/useSnackbar';
  import LessonResponseFeedbackResource from 'kolibri-common/apiResources/LessonResponseFeedbackResource';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';

  // Matches the server's limit on the length of a comment
  const MAX_COMMENT_LENGTH = 10000;

  /**
   * One learner's answers to the questions about a lesson resource, with the coach's
   * feedback on them.
   */
  export default {
    name: 'LearnerResponses',
    setup(props, { emit }) {
      const { createSnackbar } = useSnackbar();
      const editing = ref(false);
      const saving = ref(false);
      const workingComment = ref('');
      // Comment text keyed by prompt id
      const workingPromptComments = ref({});

      const hasAnswers = computed(() => Object.keys(props.answers).length > 0);

      const {
        addFeedbackAction$,
        answerFeedbackLabel$,
        editFeedbackAction$,
        feedbackLabel$,
        feedbackSaveError$,
        feedbackSavedMessage$,
        inProgressStatus$,
        noAnswerLabel$,
        notStartedStatus$,
        overallFeedbackLabel$,
        questionNumberLabel$,
        submittedStatus$,
      } = lessonResponsesStrings;
      const { cancelAction$, saveAction$ } = coreStrings;

      const status = computed(() => {
        if (props.submitted) {
          return submittedStatus$();
        }
        return hasAnswers.value ? inProgressStatus$() : notStartedStatus$();
      });

      function promptComment(prompt) {
        return props.feedback?.prompt_comments?.[prompt.id] || '';
      }

      function startEditing() {
        workingComment.value = props.feedback?.comment || '';
        workingPromptComments.value = Object.fromEntries(
          props.prompts.map(prompt => [prompt.id, promptComment(prompt)]),
        );
        editing.value = true;
      }

      async function saveFeedback() {
        const data = {
          comment: workingComment.value.trim(),
          prompt_comments: Object.fromEntries(
            Object.entries(workingPromptComments.value)
              .map(([promptId, comment]) => [promptId, comment.trim()])
              .filter(([, comment]) => comment),
          ),
        };
        saving.value = true;
        try {
          const feedback = props.feedback
            ? await LessonResponseFeedbackResource.update(props.feedback.id, data)
            : await LessonResponseFeedbackResource.create({
              ...data,
              user: props.learnerId,
              lesson_id: props.lessonId,
              contentnode_id: props.contentnodeId,
            });
          emit('feedbackSaved', feedback);
          editing.value = false;
          createSnackbar(feedbackSavedMessage$());
        } catch {
          createSnackbar(feedbackSaveError$());
        } finally {
          saving.value = false;
        }
      }

      return {
        MAX_COMMENT_LENGTH,
        editing,
        hasAnswers,
        saving,
        status,
        workingComment,
        workingPromptComments,
        promptComment,
        saveFeedback,
        startEditing,
        addFeedbackAction$,
        answerFeedbackLabel$,
        cancelAction$,
        editFeedbackAction$,
        feedbackLabel$,
        noAnswerLabel$,
        overallFeedbackLabel$,
        questionNumberLabel$,
        saveAction$,
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
      learnerId: {
        type: String,
        required: true,
      },
      learnerName: {
        type: String,
        required: true,
      },
      // Array of {id, text}
      prompts: {
        type: Array,
        required: true,
      },
      // Answer text keyed by prompt id
      answers: {
        type: Object,
        default: () => ({}),
      },
      submitted: {
        type: Boolean,
        default: false,
      },
      feedback: {
        type: Object,
        default: null,
      },
    },
  };

</script>


<style lang="scss" scoped>

  .learner-responses {
    padding: 16px 0;
    border-top: 1px solid var(--tokens-fineLine);
  }

  .learner-name {
    margin: 0;
  }

  .status {
    margin-top: 4px;
    color: var(--tokens-annotation);
  }

  .answers {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .answer-item {
    margin-bottom: 16px;
  }

  .question-heading {
    margin: 0 0 4px;
  }

  .multiline-text {
    white-space: pre-wrap;
  }

  .question {
    color: var(--tokens-annotation);
  }

  .answer {
    padding: 8px;
    background-color: var(--palette-grey-v100);
  }

  .feedback {
    padding: 8px 12px;
    border-left: 4px solid var(--tokens-primary);
  }

  .feedback-heading {
    margin: 0;
  }

</style>
