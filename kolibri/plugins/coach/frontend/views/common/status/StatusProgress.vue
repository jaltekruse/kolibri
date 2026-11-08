<template>

  <div
    v-if="show"
    class="status-progress"
    data-testid="progress-percent"
  >
    {{ $formatNumber(progress, { style: 'percent', maximumFractionDigits: 0 }) }}
  </div>

</template>


<script>

  import { computed } from 'vue';
  import { STATUSES } from '../../../modules/classSummary/constants';

  // How far a learner has got with a resource they've started, e.g. the score an HTML5 app reports
  export default {
    name: 'StatusProgress',
    setup(props) {
      const show = computed(
        () => props.status === STATUSES.started && typeof props.progress === 'number',
      );
      return { show };
    },
    props: {
      status: {
        type: String,
        required: true,
      },
      progress: {
        type: Number,
        default: null,
      },
    },
  };

</script>


<style lang="scss" scoped>

  .status-progress {
    display: block;
    margin-left: 1.75rem; /* matches KLabeledIcon */
    font-size: small;
    color: var(--tokens-annotation);
  }

</style>
