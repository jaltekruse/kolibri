<template>

  <LessonResponsesGrader
    v-if="resource"
    :lessonId="lessonId"
    :itemId="resource.contentnode_id"
    :problems="problems"
    :learners="learners"
    :title="lessonTitle"
  />

</template>


<script>

  import { computed, ref } from 'vue';
  import LessonResource from 'kolibri-common/apiResources/LessonResource';
  import LessonResponsesGrader from '../LessonResponsesGrader';

  /**
   * Learners' answers to the questions a coach wrote about a lesson resource, for the
   * coach to grade. Shows nothing if the resource has no questions, or if the lesson
   * fails to load, as then it is unknown whether it has any.
   */
  export default {
    name: 'LessonResourceResponses',
    components: {
      LessonResponsesGrader,
    },
    setup(props) {
      const lessonTitle = ref('');
      // The lesson's entry for this resource, if it has questions
      const resource = ref(null);

      async function load() {
        let lesson;
        try {
          lesson = await LessonResource.retrieve(props.lessonId);
        } catch (error) {
          // The rest of the report still works, so leave the answers out
          return;
        }
        lessonTitle.value = lesson.title;
        resource.value =
          lesson.resources.find(r => r.content_id === props.contentId && r.prompts?.length) || null;
      }

      // Questions are numbered in the order the coach wrote them
      const problems = computed(() =>
        resource.value.prompts.map((prompt, index) => ({
          key: prompt.id,
          number: String(index + 1),
          prompt: prompt.text,
        })),
      );

      load();

      return { lessonTitle, problems, resource };
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
