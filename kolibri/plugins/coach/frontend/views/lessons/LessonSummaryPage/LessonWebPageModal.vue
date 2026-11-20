<template>

  <KModal
    :title="webPage ? editWebPageTitle$() : addWebPageAction$()"
    :submitText="saveAction$()"
    :cancelText="cancelAction$()"
    :submitDisabled="saving"
    :hasError="Boolean(saveError)"
    :errorMessage="saveError ? webPageSaveError$() : null"
    @submit="handleSubmit"
    @cancel="$emit('cancel')"
  >
    <p>{{ webPagesDescription$() }}</p>
    <KTextbox
      v-model="title"
      :label="titleLabel$()"
      :maxlength="200"
      :invalid="titleInvalid"
      :invalidText="requiredFieldError$()"
      :showInvalidText="submitted"
    />
    <KTextbox
      v-model="url"
      type="url"
      :label="webPageUrlLabel$()"
      :maxlength="2000"
      :invalid="urlInvalid"
      :invalidText="webPageUrlInvalid$()"
      :showInvalidText="submitted"
    />
    <p class="hint">{{ webPageEmbedHint$() }}</p>
    <KTextbox
      v-model="instructions"
      :label="instructionsLabel$()"
      :textArea="true"
      :maxlength="1000"
    />
    <KTextbox
      v-model="problemNumbers"
      :label="problemNumbersLabel$()"
      :maxlength="500"
      :invalid="problemNumbersInvalid"
      :invalidText="problemNumbersRejected ? problemNumbersInvalid$() : requiredFieldError$()"
      :showInvalidText="submitted"
      @input="problemNumbersRejected = false"
    />
    <p class="hint">{{ problemNumbersHint$() }}</p>
  </KModal>

</template>


<script>

  import { computed, ref } from 'vue';
  import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
  import LessonWebPageResource from 'kolibri-common/apiResources/LessonWebPageResource';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
  import { isWebAddress } from 'kolibri-common/utils/lessonResponses';
  import { coachStrings } from '../../common/commonCoachStrings';

  /**
   * Adds a page from the web to a lesson, or changes one: where the page is, what
   * learners should do there, and which problems they show their work on.
   */
  export default {
    name: 'LessonWebPageModal',
    setup(props, { emit }) {
      const title = ref(props.webPage?.title || '');
      const url = ref(props.webPage?.url || '');
      const instructions = ref(props.webPage?.instructions || '');
      const problemNumbers = ref(props.webPage?.problem_numbers || '');
      // Invalid fields only show why once the coach has tried to save
      const submitted = ref(false);
      const saving = ref(false);
      const saveError = ref(null);
      // The server could not read the problem numbers
      const problemNumbersRejected = ref(false);

      const titleInvalid = computed(() => !title.value.trim());
      const urlInvalid = computed(() => !isWebAddress(url.value.trim()));
      const problemNumbersInvalid = computed(
        () => !problemNumbers.value.trim() || problemNumbersRejected.value,
      );

      async function handleSubmit() {
        submitted.value = true;
        if (titleInvalid.value || urlInvalid.value || problemNumbersInvalid.value) {
          return;
        }
        saving.value = true;
        saveError.value = null;
        const data = {
          lesson: props.lessonId,
          title: title.value.trim(),
          url: url.value.trim(),
          instructions: instructions.value.trim(),
          problem_numbers: problemNumbers.value.trim(),
        };
        try {
          const saved = props.webPage
            ? await LessonWebPageResource.update(props.webPage.id, data)
            : await LessonWebPageResource.create(data);
          emit('saved', saved);
        } catch (error) {
          const errors = error.response?.data;
          if (Array.isArray(errors) && errors.some(e => e.metadata?.field === 'problem_numbers')) {
            problemNumbersRejected.value = true;
          } else {
            saveError.value = error;
          }
        } finally {
          saving.value = false;
        }
      }

      const {
        addWebPageAction$,
        editWebPageTitle$,
        instructionsLabel$,
        problemNumbersHint$,
        problemNumbersInvalid$,
        problemNumbersLabel$,
        webPageEmbedHint$,
        webPagesDescription$,
        webPageSaveError$,
        webPageUrlInvalid$,
        webPageUrlLabel$,
      } = lessonResponsesStrings;
      const { cancelAction$, requiredFieldError$, saveAction$ } = coreStrings;
      const { titleLabel$ } = coachStrings;

      return {
        instructions,
        problemNumbers,
        problemNumbersInvalid,
        problemNumbersRejected,
        saveError,
        saving,
        submitted,
        title,
        titleInvalid,
        url,
        urlInvalid,
        handleSubmit,
        addWebPageAction$,
        cancelAction$,
        editWebPageTitle$,
        instructionsLabel$,
        problemNumbersHint$,
        problemNumbersInvalid$,
        problemNumbersLabel$,
        requiredFieldError$,
        saveAction$,
        titleLabel$,
        webPageEmbedHint$,
        webPagesDescription$,
        webPageSaveError$,
        webPageUrlInvalid$,
        webPageUrlLabel$,
      };
    },
    props: {
      lessonId: {
        type: String,
        required: true,
      },
      // The web page to change, or null to add one
      webPage: {
        type: Object,
        default: null,
      },
    },
    emits: ['saved', 'cancel'],
  };

</script>


<style lang="scss" scoped>

  .hint {
    margin-top: -8px;
    font-size: 14px;
    color: var(--tokens-annotation);
  }

</style>
