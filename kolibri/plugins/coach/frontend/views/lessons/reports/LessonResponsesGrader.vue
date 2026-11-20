<template>

  <section class="lesson-responses-grader">
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
  import LessonResponseResource from 'kolibri-common/apiResources/LessonResponseResource';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';

  /**
   * Learners' work on the problems of a lesson item, in Free Math's grading view, which
   * groups similar answers to each problem. The coach's scores and feedback are saved
   * into each learner's answer.
   */
  export default {
    name: 'LessonResponsesGrader',
    components: {
      FreeMathFrame,
    },
    setup(props) {
      const grader = ref(null);
      const loading = ref(true);
      const loadError = ref(null);
      // Free Math documents keyed by learner id, then problem key
      const answersByLearner = ref({});

      async function load() {
        try {
          const responses = await LessonResponseResource.list({
            lesson_id: props.lessonId,
            item_id: props.itemId,
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
          loadError.value = error;
        } finally {
          loading.value = false;
        }
      }

      // Learners with answers, with their answers in the order of the problems
      const students = computed(() =>
        props.learners
          .filter(learner => answersByLearner.value[learner.id])
          .map(learner => ({
            id: learner.id,
            name: learner.name,
            problems: props.problems
              .map(problem => ({
                ...problem,
                content: answersByLearner.value[learner.id][problem.key],
              }))
              .filter(problem => problem.content),
          }))
          .filter(student => student.problems.length),
      );

      function showWork() {
        grader.value.send('load-grading', {
          title: props.title,
          students: students.value,
        });
      }

      /**
       * Save grading done in the editor, one learner at a time to keep requests small.
       * @param {{[learnerId: string]: {[problemKey: string]: string}}} grades - Graded Free
       * Math documents
       * @param {function(boolean): void} respond - Tells the editor whether they were saved
       */
      async function saveGrades(grades, respond) {
        try {
          for (const [learnerId, documents] of Object.entries(grades)) {
            await LessonResponseResource.grade({
              lessonId: props.lessonId,
              itemId: props.itemId,
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
      // A lesson resource's contentnode_id, or a lesson web page's id
      itemId: {
        type: String,
        required: true,
      },
      // Array of {key, number, prompt}: how answers are saved, the problem number
      // the editor groups answers by, and the question, if any
      problems: {
        type: Array,
        required: true,
      },
      // Array of {id, name}, in the order to show them
      learners: {
        type: Array,
        required: true,
      },
      // Shown in the editor's menu bar
      title: {
        type: String,
        default: '',
      },
    },
  };

</script>


<style lang="scss" scoped>

  .lesson-responses-grader {
    margin-top: 42px;
  }

  .grader {
    height: 85vh;
    border: 1px solid var(--tokens-fineLine);
  }

</style>
