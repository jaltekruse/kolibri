<template>

  <CoachAppBarPage :loading="pageLoading">
    <KPageContainer>
      <p>
        <BackLink
          :to="lessonRoute"
          :text="backToLessonLabel$({ lesson: lesson ? lesson.title : '' })"
        />
      </p>
      <KCircularLoader v-if="loading" />
      <p
        v-else-if="loadError"
        role="alert"
      >
        {{ webPagesLoadError$() }}
      </p>
      <template v-else>
        <h1>{{ webPage.title }}</h1>
        <p>
          <KExternalLink
            :href="webPage.url"
            :text="openWebPageAction$()"
            :openInNewTab="true"
          />
        </p>
        <p
          v-if="webPage.instructions"
          class="instructions"
        >
          <span class="multiline-text">{{ webPage.instructions }}</span>
        </p>
        <p>{{ problemsListLabel$({ problems: webPage.problem_numbers }) }}</p>
        <LessonResponsesGrader
          :lessonId="lessonId"
          :itemId="webPage.id"
          :problems="problems"
          :learners="learners"
          :title="webPage.title"
        />
      </template>
    </KPageContainer>
  </CoachAppBarPage>

</template>


<script>

  import sortBy from 'lodash/sortBy';
  import { computed, ref } from 'vue';
  import { useRoute } from 'vue-router/composables';
  import usePageTitle from 'kolibri/composables/usePageTitle';
  import { pageLoading } from 'kolibri-common/composables/usePageLoading';
  import LessonWebPageResource from 'kolibri-common/apiResources/LessonWebPageResource';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
  import { PageNames } from '../../../constants';
  import store from '../../../store';
  import CoachAppBarPage from '../../CoachAppBarPage';
  import BackLink from '../../common/BackLink';
  import { coachStrings } from '../../common/commonCoachStrings';
  import LessonResponsesGrader from './LessonResponsesGrader';

  /**
   * A page from the web in a lesson, with the work learners showed on its problems, for
   * the coach to grade.
   */
  export default {
    name: 'LessonWebPageReportPage',
    components: {
      BackLink,
      CoachAppBarPage,
      LessonResponsesGrader,
    },
    setup() {
      const route = useRoute();
      const { classId, lessonId, webPageId } = route.params;
      const webPage = ref(null);
      const loading = ref(true);
      const loadError = ref(null);

      const lesson = computed(() => store.state.classSummary.lessonMap[lessonId]);

      // The learners the lesson is assigned to, by name
      const learners = computed(() => {
        if (!lesson.value) {
          return [];
        }
        const { learnerMap } = store.state.classSummary;
        const learnerIds = store.getters['classSummary/getLearnersForLesson'](lesson.value);
        return sortBy(
          learnerIds.map(id => learnerMap[id]),
          ['name'],
        );
      });

      // Problems are numbered as the coach listed them
      const problems = computed(() =>
        webPage.value.problems.map(number => ({ key: number, number, prompt: '' })),
      );

      const lessonRoute = {
        name: PageNames.LESSON_SUMMARY,
        params: { classId, lessonId },
      };

      async function load() {
        try {
          webPage.value = await LessonWebPageResource.retrieve(webPageId);
        } catch (error) {
          loadError.value = error;
        } finally {
          loading.value = false;
        }
      }

      usePageTitle(
        () => [webPage.value?.title, lesson.value?.title, store.state.classSummary.name],
        { hasVisibleHeading: true },
      );

      load();

      const { openWebPageAction$, problemsListLabel$, webPagesLoadError$ } = lessonResponsesStrings;
      const { backToLessonLabel$ } = coachStrings;

      return {
        learners,
        lesson,
        lessonId,
        lessonRoute,
        loadError,
        loading,
        pageLoading,
        problems,
        webPage,
        backToLessonLabel$,
        openWebPageAction$,
        problemsListLabel$,
        webPagesLoadError$,
      };
    },
  };

</script>


<style lang="scss" scoped>

  .multiline-text {
    white-space: pre-wrap;
  }

</style>
