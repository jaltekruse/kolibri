<template>

  <KModal
    :title="editQuestionsAction$()"
    :submitText="saveAction$()"
    :cancelText="cancelAction$()"
    @submit="handleSubmit"
    @cancel="$emit('cancel')"
  >
    <p class="resource-title">
      {{ resourceTitle }}
    </p>
    <p>{{ editQuestionsDescription$() }}</p>

    <ol class="prompts">
      <li
        v-for="(prompt, index) in workingPrompts"
        :key="prompt.id"
        class="prompt"
      >
        <KTextbox
          v-model="prompt.text"
          class="prompt-textbox"
          :label="questionNumberLabel$({ number: index + 1 })"
          :textArea="true"
          :maxlength="MAX_PROMPT_LENGTH"
        />
        <KIconButton
          icon="trash"
          :ariaLabel="removeQuestionAction$({ number: index + 1 })"
          @click="removePrompt(index)"
        />
      </li>
    </ol>

    <KButton
      appearance="flat-button"
      icon="plus"
      :text="addQuestionAction$()"
      @click="addPrompt"
    />
  </KModal>

</template>


<script>

  import { ref } from 'vue';
  import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
  import { createPrompt } from 'kolibri-common/utils/lessonResponses';

  // Matches the server's limit on the length of a prompt
  const MAX_PROMPT_LENGTH = 1000;

  /**
   * Edits the questions about a lesson resource that learners show their work on in the
   * math editor.
   */
  export default {
    name: 'LessonResourcePromptsModal',
    setup(props, { emit }) {
      const workingPrompts = ref(
        props.prompts.length ? props.prompts.map(prompt => ({ ...prompt })) : [createPrompt()],
      );

      function addPrompt() {
        workingPrompts.value = [...workingPrompts.value, createPrompt()];
      }

      function removePrompt(index) {
        workingPrompts.value = workingPrompts.value.filter((_, i) => i !== index);
      }

      function handleSubmit() {
        emit(
          'submit',
          workingPrompts.value
            .map(prompt => ({ id: prompt.id, text: prompt.text.trim() }))
            .filter(prompt => prompt.text),
        );
      }

      const {
        addQuestionAction$,
        editQuestionsAction$,
        editQuestionsDescription$,
        questionNumberLabel$,
        removeQuestionAction$,
      } = lessonResponsesStrings;
      const { cancelAction$, saveAction$ } = coreStrings;

      return {
        MAX_PROMPT_LENGTH,
        workingPrompts,
        addPrompt,
        handleSubmit,
        removePrompt,
        addQuestionAction$,
        cancelAction$,
        editQuestionsAction$,
        editQuestionsDescription$,
        questionNumberLabel$,
        removeQuestionAction$,
        saveAction$,
      };
    },
    props: {
      resourceTitle: {
        type: String,
        required: true,
      },
      // Array of {id, text}
      prompts: {
        type: Array,
        default: () => [],
      },
    },
  };

</script>


<style lang="scss" scoped>

  .resource-title {
    font-weight: bold;
  }

  .prompts {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .prompt {
    display: flex;
    align-items: flex-start;
  }

  .prompt-textbox {
    flex: 1 1 auto;
    max-width: none;
  }

</style>
