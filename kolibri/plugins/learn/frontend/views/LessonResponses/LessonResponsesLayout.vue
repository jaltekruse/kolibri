<template>

  <!-- The resource stays in the same element whether or not there are prompts,
       so it is not remounted once the prompts load. -->
  <div :class="{ 'side-by-side': sideBySide }">
    <div class="resource">
      <slot></slot>
    </div>
    <LessonResponsesPanel
      v-if="prompts.length"
      :key="`${lessonId}:${contentnodeId}`"
      class="responses"
      :lessonId="lessonId"
      :contentnodeId="contentnodeId"
      :prompts="prompts"
      :title="title"
    />
  </div>

</template>


<script>

  import { computed, ref, watch } from 'vue';
  import useKResponsiveWindow from 'kolibri-design-system/lib/composables/useKResponsiveWindow';
  import { LearnerLessonResource } from '../../apiResources';
  import LessonResponsesPanel from './LessonResponsesPanel';

  /**
   * Shows a lesson resource alongside the questions a coach wrote about it, if any:
   * side by side on large windows, and with the questions below the resource otherwise.
   */
  export default {
    name: 'LessonResponsesLayout',
    components: {
      LessonResponsesPanel,
    },
    setup(props) {
      const { windowIsLarge } = useKResponsiveWindow();
      const prompts = ref([]);

      async function fetchPrompts() {
        prompts.value = [];
        const { lessonId, contentnodeId } = props;
        if (!lessonId || !contentnodeId) {
          return;
        }
        const lesson = await LearnerLessonResource.retrieve(lessonId);
        // Ignore the response if the learner has moved on to another resource
        if (lessonId !== props.lessonId || contentnodeId !== props.contentnodeId) {
          return;
        }
        const resource = lesson.resources.find(r => r.contentnode_id === contentnodeId);
        prompts.value = resource?.prompts || [];
      }

      watch(() => [props.lessonId, props.contentnodeId], fetchPrompts, { immediate: true });

      const sideBySide = computed(() => prompts.value.length > 0 && windowIsLarge.value);

      return { prompts, sideBySide };
    },
    props: {
      // Only set when the resource is being viewed as part of a lesson
      lessonId: {
        type: String,
        default: null,
      },
      contentnodeId: {
        type: String,
        default: null,
      },
      // Title of the resource
      title: {
        type: String,
        default: '',
      },
    },
  };

</script>


<style lang="scss" scoped>

  .side-by-side {
    display: flex;
    align-items: flex-start;

    .resource {
      flex: 1 1 auto;
      min-width: 0;
    }

    .responses {
      // The math editor needs room for steps of work
      flex: 0 0 50%;
      // Same height as the content viewer, so the resource stays in view
      // while learners work on the questions
      height: calc(100vh - 61px);
      overflow-y: auto;
      border-left: 1px solid var(--tokens-fineLine);
    }
  }

</style>
