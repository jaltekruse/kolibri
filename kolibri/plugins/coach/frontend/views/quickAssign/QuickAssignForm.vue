<template>

  <form
    class="quick-assign-form"
    @submit.prevent="create"
  >
    <fieldset>
      <legend>{{ whatToAssignLabel$() }}</legend>
      <KRadioButtonGroup>
        <KRadioButton
          v-model="kind"
          :buttonValue="EXERCISES"
          :label="exercisesOption$()"
        />
        <KRadioButton
          v-model="kind"
          :buttonValue="FREE_MATH"
          :label="freeMathOption$()"
        />
      </KRadioButtonGroup>
    </fieldset>

    <template v-if="kind === EXERCISES">
      <div class="search">
        <KTextbox
          v-model="search"
          :label="searchExercisesLabel$()"
          type="search"
          @keydown.enter.prevent="searchExercises"
        />
        <KButton
          :text="searchLabel$()"
          :disabled="!search.trim() || searching"
          @click="searchExercises"
        />
      </div>
      <p
        v-if="searchError"
        role="alert"
      >
        {{ exerciseSearchError$() }}
      </p>
      <p v-else-if="searchedFor && !results.length">{{ noExercisesFound$() }}</p>
      <ul
        v-else-if="results.length"
        class="exercises"
      >
        <li
          v-for="exercise in results"
          :key="exercise.id"
        >
          <span>{{ exercise.title }}</span>
          <KButton
            appearance="flat-button"
            :text="addAction$()"
            :aria-label="addExerciseAction$({ title: exercise.title })"
            :disabled="isChosen(exercise)"
            @click="choose(exercise)"
          />
        </li>
      </ul>

      <h2>{{ chosenExercisesLabel$() }}</h2>
      <ul
        v-if="chosen.length"
        class="exercises"
      >
        <li
          v-for="exercise in chosen"
          :key="exercise.id"
        >
          <span>{{ exercise.title }}</span>
          <KIconButton
            icon="close"
            :ariaLabel="removeExerciseAction$({ title: exercise.title })"
            @click="unchoose(exercise)"
          />
        </li>
      </ul>
      <p
        v-else
        :class="{ invalid: submitted }"
      >
        {{ chooseExercisesHint$() }}
      </p>
    </template>

    <template v-else>
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
    </template>

    <KTextbox
      v-model="title"
      :label="assignmentTitleLabel$()"
      :maxlength="TITLE_MAX_LENGTH"
      :invalid="titleInvalid"
      :invalidText="requiredFieldError$()"
      :showInvalidText="submitted"
    />

    <p
      v-if="saveError"
      role="alert"
    >
      {{ createError$() }}
    </p>
    <KButton
      primary
      type="submit"
      :text="createLinkAction$()"
      :disabled="saving"
    />
  </form>

</template>


<script>

  import { computed, ref } from 'vue';
  import ContentNodeResource from 'kolibri-common/apiResources/ContentNodeResource';
  import QuickAssignmentResource from 'kolibri-common/apiResources/QuickAssignmentResource';
  import useUser from 'kolibri/composables/useUser';
  import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
  import { quickAssignStrings } from 'kolibri-common/strings/quickAssignStrings';
  import { isWebAddress } from 'kolibri-common/utils/lessonResponses';

  const EXERCISES = 'exercises';
  const FREE_MATH = 'freeMath';
  // As long as a lesson title can be
  const TITLE_MAX_LENGTH = 50;
  const SEARCH_RESULTS = 10;

  /**
   * Makes a quick assignment: exercises from the library, or problems on a web page that
   * students show their work on in Free Math.
   */
  export default {
    name: 'QuickAssignForm',
    setup(props, { emit }) {
      const { full_name } = useUser();
      const kind = ref(EXERCISES);
      const title = ref('');
      const search = ref('');
      const searchedFor = ref('');
      const searching = ref(false);
      const searchError = ref(null);
      const results = ref([]);
      const chosen = ref([]);
      const url = ref('');
      const instructions = ref('');
      const problemNumbers = ref('');
      // Invalid fields only show why once the coach has tried to create the assignment
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
      const formInvalid = computed(() => {
        if (titleInvalid.value) {
          return true;
        }
        if (kind.value === EXERCISES) {
          return !chosen.value.length;
        }
        return urlInvalid.value || problemNumbersInvalid.value;
      });

      function isChosen(exercise) {
        return chosen.value.some(({ id }) => id === exercise.id);
      }

      function choose(exercise) {
        if (isChosen(exercise)) {
          return;
        }
        chosen.value = [...chosen.value, exercise];
        if (!title.value.trim()) {
          title.value = exercise.title.slice(0, TITLE_MAX_LENGTH);
        }
      }

      function unchoose(exercise) {
        chosen.value = chosen.value.filter(({ id }) => id !== exercise.id);
      }

      async function searchExercises() {
        const keywords = search.value.trim();
        if (!keywords) {
          return;
        }
        searching.value = true;
        searchError.value = null;
        try {
          const response = await ContentNodeResource.list({
            search: keywords,
            kind: 'exercise',
            max_results: SEARCH_RESULTS,
          });
          results.value = response.results;
          searchedFor.value = keywords;
        } catch (error) {
          searchError.value = error;
        } finally {
          searching.value = false;
        }
      }

      async function chooseExercise(exerciseId) {
        try {
          choose(await ContentNodeResource.retrieve(exerciseId));
        } catch (error) {
          // Not in the library: the coach can search for it instead
        }
      }

      async function create() {
        submitted.value = true;
        if (formInvalid.value) {
          return;
        }
        saving.value = true;
        saveError.value = null;
        const data = {
          title: title.value.trim(),
          classroom_name: quickAssignClassName$({ name: full_name.value }),
        };
        if (kind.value === EXERCISES) {
          data.exercise_ids = chosen.value.map(({ id }) => id);
        } else {
          data.web_page = {
            url: url.value.trim(),
            instructions: instructions.value.trim(),
            problem_numbers: problemNumbers.value.trim(),
          };
        }
        try {
          emit('created', await QuickAssignmentResource.create(data));
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

      if (props.exerciseId) {
        chooseExercise(props.exerciseId);
      }

      const {
        addAction$,
        addExerciseAction$,
        assignmentTitleLabel$,
        chooseExercisesHint$,
        chosenExercisesLabel$,
        createError$,
        createLinkAction$,
        exerciseSearchError$,
        exercisesOption$,
        freeMathOption$,
        noExercisesFound$,
        quickAssignClassName$,
        removeExerciseAction$,
        searchExercisesLabel$,
        whatToAssignLabel$,
      } = quickAssignStrings;
      const {
        instructionsLabel$,
        problemNumbersHint$,
        problemNumbersInvalid$,
        problemNumbersLabel$,
        webPageEmbedHint$,
        webPageUrlInvalid$,
        webPageUrlLabel$,
      } = lessonResponsesStrings;
      const { requiredFieldError$, searchLabel$ } = coreStrings;

      return {
        EXERCISES,
        FREE_MATH,
        TITLE_MAX_LENGTH,
        chosen,
        instructions,
        kind,
        problemNumbers,
        problemNumbersInvalid,
        problemNumbersRejected,
        results,
        saveError,
        saving,
        search,
        searchError,
        searchedFor,
        searching,
        submitted,
        title,
        titleInvalid,
        url,
        urlInvalid,
        choose,
        create,
        isChosen,
        searchExercises,
        unchoose,
        addAction$,
        addExerciseAction$,
        assignmentTitleLabel$,
        chooseExercisesHint$,
        chosenExercisesLabel$,
        createError$,
        createLinkAction$,
        exerciseSearchError$,
        exercisesOption$,
        freeMathOption$,
        instructionsLabel$,
        noExercisesFound$,
        problemNumbersHint$,
        problemNumbersInvalid$,
        problemNumbersLabel$,
        removeExerciseAction$,
        requiredFieldError$,
        searchLabel$,
        searchExercisesLabel$,
        webPageEmbedHint$,
        webPageUrlInvalid$,
        webPageUrlLabel$,
        whatToAssignLabel$,
      };
    },
    props: {
      // An exercise to start with, such as one a coach chose to quick assign in Learn
      exerciseId: {
        type: String,
        default: null,
      },
    },
    emits: ['created'],
  };

</script>


<style lang="scss" scoped>

  .quick-assign-form {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-width: 640px;
  }

  fieldset {
    padding: 0;
    margin: 0 0 8px;
    border: 0;
  }

  legend {
    margin-bottom: 8px;
    font-weight: bold;
  }

  .search {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .exercises {
    padding: 0;
    margin: 0;
    list-style: none;

    li {
      display: flex;
      gap: 8px;
      align-items: center;
      justify-content: space-between;
      padding: 4px 0;
      border-bottom: 1px solid var(--tokens-fineLine);
    }
  }

  h2 {
    margin: 16px 0 0;
    font-size: 16px;
  }

  .hint {
    margin-top: -8px;
    font-size: 14px;
    color: var(--tokens-annotation);
  }

  .invalid {
    color: var(--tokens-error);
  }

</style>
