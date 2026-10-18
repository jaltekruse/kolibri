<template>

  <section
    v-if="prompts.length"
    class="lesson-resource-responses"
  >
    <h2>{{ learnerAnswersLabel$() }}</h2>
    <KCircularLoader v-if="loading" />
    <p
      v-else-if="loadError"
      role="alert"
    >
      {{ learnerAnswersLoadError$() }}
    </p>
    <p
      v-else-if="!students.length"
      data-testid="no-answers"
    >
      {{ noAnswersYetStatus$() }}
    </p>
    <FreeMathFrame
      v-else
      ref="grader"
      class="grader"
      mode="grader"
      :title="gradingEditorLabel$()"
      @ready="showWork"
      @saveGrades="saveGrades"
    />
  </section>

</template>


<script>

  import { computed, ref } from 'vue';
  import FreeMathFrame from 'kolibri-common/components/FreeMathFrame';
  import LessonResource from 'kolibri-common/apiResources/LessonResource';
  import LessonResponseResource from 'kolibri-common/apiResources/LessonResponseResource';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';

  /**
   * Learners' work on the questions a coach wrote about a lesson resource, in Free Math's
   * grading view, which groups similar answers to each question. The coach's scores and
   * feedback are saved into each learner's answer. Shows nothing if the resource has no
   * questions.
   */
  export default {
    name: 'LessonResourceResponses',
    components: {
      FreeMathFrame,
    },
    setup(props) {
      const grader = ref(null);
      const lessonTitle = ref('');
      const prompts = ref([]);
      const contentnodeId = ref(null);
      const loading = ref(true);
      const loadError = ref(null);
      // Free Math documents keyed by learner id, then prompt id
      const answersByLearner = ref({});

      async function load() {
        try {
          const lesson = await LessonResource.retrieve(props.lessonId);
          const resource = lesson.resources.find(
            r => r.content_id === props.contentId && r.prompts?.length,
          );
          if (!resource) {
            return;
          }
          lessonTitle.value = lesson.title;
          contentnodeId.value = resource.contentnode_id;
          prompts.value = resource.prompts;
          const responses = await LessonResponseResource.list({
            lesson_id: props.lessonId,
            contentnode_id: resource.contentnode_id,
          });
          const byLearner = {};
          for (const response of responses) {
            byLearner[response.user] = {
              ...byLearner[response.user],
              [response.item]: response.answer.free_math,
            };
          }
          answersByLearner.value = byLearner;
        } catch (error) {
          // If the lesson itself failed to load, it is unknown whether the resource
          // has questions, so nothing is shown.
          loadError.value = error;
        } finally {
          loading.value = false;
        }
      }

      // Learners with answers, with their answers in the order of the questions
      const students = computed(() =>
        props.learners
          .filter(learner => answersByLearner.value[learner.id])
          .map(learner => ({
            id: learner.id,
            name: learner.name,
            problems: prompts.value
              .map((prompt, index) => ({
                key: prompt.id,
                number: String(index + 1),
                prompt: prompt.text,
                content: answersByLearner.value[learner.id][prompt.id],
              }))
              .filter(problem => problem.content),
          })),
      );

      function showWork() {
        grader.value.send('load-grading', {
          title: lessonTitle.value,
          students: students.value,
        });
      }

      /**
       * Save grading done in the editor, one learner at a time to keep requests small.
       * @param {{[learnerId: string]: {[promptId: string]: string}}} grades - Graded Free Math
       * documents
       * @param {function(boolean): void} respond - Tells the editor whether they were saved
       */
      async function saveGrades(grades, respond) {
        try {
          for (const [learnerId, documents] of Object.entries(grades)) {
            await LessonResponseResource.grade({
              lessonId: props.lessonId,
              contentnodeId: contentnodeId.value,
              grades: { [learnerId]: documents },
            });
            answersByLearner.value = {
              ...answersByLearner.value,
              [learnerId]: { ...answersByLearner.value[learnerId], ...documents },
            };
          }
          respond(true);
        } catch (error) {
          respond(false);
        }
      }

      load();

      const {
        gradingEditorLabel$,
        learnerAnswersLabel$,
        learnerAnswersLoadError$,
        noAnswersYetStatus$,
      } = lessonResponsesStrings;

      return {
        grader,
        loadError,
        loading,
        prompts,
        students,
        saveGrades,
        showWork,
        gradingEditorLabel$,
        learnerAnswersLabel$,
        learnerAnswersLoadError$,
        noAnswersYetStatus$,
      };
    },
    props: {
      lessonId: {
        type: String,
        required: true,
      },
      // The content_id of the lesson resource
      contentId: {
        type: String,
        required: true,
      },
      // Array of {id, name}, in the order to show them
      learners: {
        type: Array,
        required: true,
      },
    },
  };

</script>


<style lang="scss" scoped>

  .lesson-resource-responses {
    margin-top: 42px;
  }

  .grader {
    height: 85vh;
    border: 1px solid var(--tokens-fineLine);
  }

</style>
