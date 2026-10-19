<template>

  <ul class="quick-assignments">
    <li
      v-for="assignment in assignments"
      :key="assignment.id"
      class="quick-assignment"
    >
      <h3>{{ assignment.title }}</h3>
      <ShareLink :link="assignment.link" />
      <div class="details">
        <span>{{ joinedCountLabel$({ count: assignment.learner_count }) }}</span>
        <KSwitch
          :name="`link-open-${assignment.id}`"
          :label="linkOpenLabel$()"
          :value="assignment.is_open"
          :disabled="updating.includes(assignment.id)"
          @change="setOpen(assignment, $event)"
        />
        <KRouterLink
          :text="viewResultsAction$()"
          :to="{
            name: PageNames.LESSON_SUMMARY,
            params: { classId: assignment.classroom_id, lessonId: assignment.id },
          }"
        />
      </div>
    </li>
  </ul>

</template>


<script>

  import { ref } from 'vue';
  import QuickAssignmentResource from 'kolibri-common/apiResources/QuickAssignmentResource';
  import { quickAssignStrings } from 'kolibri-common/strings/quickAssignStrings';
  import { PageNames } from '../../constants';
  import ShareLink from './ShareLink';

  /**
   * A coach's quick assignments, each with its link, how many students joined, whether
   * new students can still join, and a link to their work.
   */
  export default {
    name: 'QuickAssignmentList',
    components: { ShareLink },
    setup(props, { emit }) {
      // Assignments with changes on their way to the server
      const updating = ref([]);

      async function setOpen(assignment, isOpen) {
        updating.value = [...updating.value, assignment.id];
        try {
          emit('updated', await QuickAssignmentResource.update(assignment.id, { is_open: isOpen }));
        } finally {
          updating.value = updating.value.filter(id => id !== assignment.id);
        }
      }

      const { joinedCountLabel$, linkOpenLabel$, viewResultsAction$ } = quickAssignStrings;

      return {
        PageNames,
        updating,
        setOpen,
        joinedCountLabel$,
        linkOpenLabel$,
        viewResultsAction$,
      };
    },
    props: {
      assignments: {
        type: Array,
        required: true,
      },
    },
    emits: ['updated'],
  };

</script>


<style lang="scss" scoped>

  .quick-assignments {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .quick-assignment {
    padding: 16px 0;
    border-bottom: 1px solid var(--tokens-fineLine);

    h3 {
      margin: 0 0 8px;
    }
  }

  .details {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 24px;
    align-items: center;
    margin-top: 8px;
  }

</style>
