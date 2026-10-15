<template>

  <section
    v-if="prompts.length"
    class="lesson-resource-responses"
  >
    <h2>{{ learnerAnswersLabel$() }}</h2>
    <KCircularLoader v-if="loading" />
    <template v-else>
      <LearnerResponses
        v-for="learner in learners"
        :key="learner.id"
        :data-testid="`learner-${learner.id}`"
        :lessonId="lessonId"
        :contentnodeId="contentnodeId"
        :learnerId="learner.id"
        :learnerName="learner.name"
        :prompts="prompts"
        :answers="responsesFor(learner).answers"
        :submitted="responsesFor(learner).submitted"
        :feedback="feedbackByLearner[learner.id] || null"
        @feedbackSaved="setFeedback"
      />
    </template>
  </section>

</template>


<script>

  import { ref } from 'vue';
  import LessonResource from 'kolibri-common/apiResources/LessonResource';
  import LessonResponseResource from 'kolibri-common/apiResources/LessonResponseResource';
  import LessonResponseFeedbackResource from 'kolibri-common/apiResources/LessonResponseFeedbackResource';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
  import LearnerResponses from './LearnerResponses';

  const NO_RESPONSES = Object.freeze({ answers: {}, submitted: false });

  /**
   * Learners' answers to the questions a coach wrote about a lesson resource,
   * and the coach's feedback on them. Shows nothing if the resource has no questions.
   */
  export default {
    name: 'LessonResourceResponses',
    components: {
      LearnerResponses,
    },
    setup(props) {
      const prompts = ref([]);
      const contentnodeId = ref(null);
      const loading = ref(true);
      // {answers, submitted} keyed by learner id
      const responsesByLearner = ref({});
      // Feedback keyed by learner id
      const feedbackByLearner = ref({});

      async function load() {
        try {
          const lesson = await LessonResource.retrieve(props.lessonId);
          const resource = lesson.resources.find(
            r => r.content_id === props.contentId && r.prompts?.length,
          );
          if (!resource) {
            return;
          }
          contentnodeId.value = resource.contentnode_id;
          prompts.value = resource.prompts;
          const params = { lesson_id: props.lessonId, contentnode_id: resource.contentnode_id };
          const [responses, feedbackList] = await Promise.all([
            LessonResponseResource.list(params),
            LessonResponseFeedbackResource.list(params),
          ]);
          const byLearner = {};
          for (const response of responses) {
            if (!byLearner[response.user]) {
              byLearner[response.user] = { answers: {}, submitted: false };
            }
            byLearner[response.user].answers[response.item] = response.answer.text;
            byLearner[response.user].submitted =
              byLearner[response.user].submitted || response.complete;
          }
          responsesByLearner.value = byLearner;
          feedbackByLearner.value = Object.fromEntries(
            feedbackList.map(feedback => [feedback.user, feedback]),
          );
        } finally {
          loading.value = false;
        }
      }

      function responsesFor(learner) {
        return responsesByLearner.value[learner.id] || NO_RESPONSES;
      }

      function setFeedback(feedback) {
        feedbackByLearner.value = { ...feedbackByLearner.value, [feedback.user]: feedback };
      }

      load();

      const { learnerAnswersLabel$ } = lessonResponsesStrings;

      return {
        contentnodeId,
        feedbackByLearner,
        loading,
        prompts,
        responsesFor,
        setFeedback,
        learnerAnswersLabel$,
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

</style>
