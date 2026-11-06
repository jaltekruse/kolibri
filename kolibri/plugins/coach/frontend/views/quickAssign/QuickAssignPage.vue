<template>

  <CoachAppBarPage :appBarTitle="quickAssignAction$()">
    <KPageContainer>
      <h1>{{ quickAssignAction$() }}</h1>
      <p>{{ quickAssignDescription$() }}</p>

      <QuickAssignForm
        :key="formKey"
        :exerciseId="$route.query.exercise || null"
        @created="handleCreated"
      />

      <section
        v-if="created"
        class="ready"
        role="status"
      >
        <p>{{ linkReadyMessage$({ title: created.title }) }}</p>
        <ShareLink :link="created.link" />
      </section>

      <h2>{{ yourQuickAssignmentsLabel$() }}</h2>
      <KCircularLoader v-if="loading" />
      <p
        v-else-if="loadError"
        role="alert"
      >
        {{ quickAssignmentsLoadError$() }}
      </p>
      <p v-else-if="!assignments.length">{{ noQuickAssignments$() }}</p>
      <QuickAssignmentList
        v-else
        :assignments="assignments"
        @updated="handleUpdated"
      />
    </KPageContainer>
  </CoachAppBarPage>

</template>


<script>

  import { ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router/composables';
  import usePageTitle from 'kolibri/composables/usePageTitle';
  import QuickAssignmentResource from 'kolibri-common/apiResources/QuickAssignmentResource';
  import { quickAssignStrings } from 'kolibri-common/strings/quickAssignStrings';
  import CoachAppBarPage from '../CoachAppBarPage';
  import QuickAssignForm from './QuickAssignForm';
  import QuickAssignmentList from './QuickAssignmentList';
  import ShareLink from './ShareLink';

  /**
   * Where a coach makes assignments anyone with the link can join, without a class, and
   * finds the ones they made.
   */
  export default {
    name: 'QuickAssignPage',
    components: {
      CoachAppBarPage,
      QuickAssignForm,
      QuickAssignmentList,
      ShareLink,
    },
    setup() {
      const route = useRoute();
      const router = useRouter();
      const assignments = ref([]);
      const loading = ref(true);
      const loadError = ref(null);
      // The assignment just made, to share
      const created = ref(null);
      // Changes to start the form afresh after making an assignment
      const formKey = ref(0);

      async function load() {
        try {
          assignments.value = await QuickAssignmentResource.list();
        } catch (error) {
          loadError.value = error;
        } finally {
          loading.value = false;
        }
      }

      async function handleCreated(assignment) {
        created.value = assignment;
        assignments.value = [assignment, ...assignments.value];
        // Start the next assignment afresh, without the exercise chosen in Learn
        if (route.query.exercise) {
          await router.replace({ query: {} });
        }
        formKey.value += 1;
      }

      function handleUpdated(assignment) {
        assignments.value = assignments.value.map(existing =>
          existing.id === assignment.id ? assignment : existing,
        );
      }

      const {
        linkReadyMessage$,
        noQuickAssignments$,
        quickAssignAction$,
        quickAssignDescription$,
        quickAssignmentsLoadError$,
        yourQuickAssignmentsLabel$,
      } = quickAssignStrings;

      usePageTitle(() => quickAssignAction$(), { hasVisibleHeading: true });

      load();

      return {
        assignments,
        created,
        formKey,
        loadError,
        loading,
        handleCreated,
        handleUpdated,
        linkReadyMessage$,
        noQuickAssignments$,
        quickAssignAction$,
        quickAssignDescription$,
        quickAssignmentsLoadError$,
        yourQuickAssignmentsLabel$,
      };
    },
  };

</script>


<style lang="scss" scoped>

  .ready {
    padding: 16px;
    margin-top: 16px;
    background-color: var(--palette-grey-v100);
    border-radius: 4px;

    p {
      margin-top: 0;
    }
  }

</style>
