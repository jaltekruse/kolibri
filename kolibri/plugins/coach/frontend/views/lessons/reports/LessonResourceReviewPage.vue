<template>

  <CoachAppBarPage :loading="pageLoading">
    <KPageContainer>
      <BackLink
        :to="backLink"
        :text="backToReportLabel$()"
      />
      <h1>{{ reviewWorkTitle$({ title: resource ? resource.title : '' }) }}</h1>
      <p>{{ reviewWorkDescription$() }}</p>
      <KCircularLoader v-if="loading" />
      <ContentViewer
        v-else-if="resource"
        class="review-viewer"
        :contentNode="resource"
        :extraFields="extraFields"
        @updateContentState="saveFeedback"
      />
      <p
        v-if="saveFailed"
        role="alert"
        class="save-error"
      >
        {{ feedbackNotSavedMessage$() }}
      </p>
    </KPageContainer>
  </CoachAppBarPage>

</template>


<script>

  import { computed, ref, watch } from 'vue';
  import { useRoute } from 'vue-router/composables';
  import usePageTitle from 'kolibri/composables/usePageTitle';
  import { pageLoading } from 'kolibri-common/composables/usePageLoading';
  import router from 'kolibri/router';
  import { PageNames } from '../../../constants';
  import ContentSummaryLogResource from '../../../apiResources/contentSummaryLog';
  import ContentFeedbackLogResource from '../../../apiResources/contentFeedbackLog';
  import CoachAppBarPage from '../../CoachAppBarPage';
  import BackLink from '../../common/BackLink';
  import store from '../../../store';
  import { reviewStrings as strings } from './reviewStrings';

  // The localStorage key resources find learners' work to review in
  export const REVIEW_STORAGE_KEY = 'kolibri:review';
  // The localStorage keys resources put feedback to each learner in
  export const FEEDBACK_STORAGE_KEY_PREFIX = 'kolibri:feedback:';

  function contentStorage(extraFields) {
    return (extraFields && extraFields.contentState && extraFields.contentState.localStorage) || {};
  }

  export default {
    name: 'LessonResourceReviewPage',
    components: {
      BackLink,
      CoachAppBarPage,
    },
    setup() {
      const route = useRoute();
      const {
        reviewWorkTitle$,
        reviewWorkDescription$,
        backToReportLabel$,
        feedbackNotSavedMessage$,
      } = strings;

      const resource = computed(() => store.state.resourceDetail.resource);
      const lesson = computed(() => store.state.classSummary.lessonMap[route.params.lessonId]);
      const contentId = computed(() => route.params.resourceId);

      usePageTitle(
        () => [resource.value?.title, lesson.value?.title, store.state.classSummary.name],
        { hasVisibleHeading: true },
      );

      const loading = ref(true);
      const saveFailed = ref(false);
      const extraFields = ref({});
      // The feedback to each learner, as the resource last gave it, to only save what changes
      let savedFeedback = {};

      async function loadWork() {
        loading.value = true;
        const params = { content_id: contentId.value, classroom: route.params.classId };
        const [logs, feedbackLogs] = await Promise.all([
          ContentSummaryLogResource.list(params),
          ContentFeedbackLogResource.list(params),
        ]);
        const work = {};
        for (const log of logs) {
          work[log.user] = contentStorage(log.extra_fields);
        }
        const feedback = {};
        for (const log of feedbackLogs) {
          feedback[log.user] = log.data;
        }
        const learnerMap = store.state.classSummary.learnerMap;
        const learners = store.getters['classSummary/getLearnersForLesson'](lesson.value)
          .filter(id => learnerMap[id])
          .map(id => ({
            id,
            name: learnerMap[id].name,
            work: work[id] || null,
            feedback: feedback[id] || null,
          }));
        savedFeedback = {};
        for (const learner of learners) {
          if (learner.feedback) {
            savedFeedback[learner.id] = JSON.stringify(learner.feedback);
          }
        }
        extraFields.value = {
          contentState: {
            localStorage: { [REVIEW_STORAGE_KEY]: JSON.stringify({ learners }) },
          },
        };
        loading.value = false;
      }

      watch([contentId, lesson], () => lesson.value && loadWork(), { immediate: true });

      async function saveFeedback(contentState) {
        const storage = (contentState && contentState.localStorage) || {};
        const changed = Object.keys(storage).filter(
          key =>
            key.startsWith(FEEDBACK_STORAGE_KEY_PREFIX) &&
            storage[key] !== savedFeedback[key.slice(FEEDBACK_STORAGE_KEY_PREFIX.length)],
        );
        const saves = changed.map(key => {
          const user = key.slice(FEEDBACK_STORAGE_KEY_PREFIX.length);
          const value = storage[key];
          savedFeedback[user] = value;
          return ContentFeedbackLogResource.create({
            user,
            content_id: contentId.value,
            channel_id: resource.value.channel_id,
            data: JSON.parse(value),
          }).catch(() => {
            delete savedFeedback[user];
            return Promise.reject();
          });
        });
        try {
          await Promise.all(saves);
          saveFailed.value = false;
        } catch (e) {
          saveFailed.value = true;
        }
      }

      const backLink = computed(() =>
        router.getRoute(PageNames.LESSON_RESOURCE_LEARNERS_REPORT, {
          classId: route.params.classId,
          lessonId: route.params.lessonId,
          resourceId: route.params.resourceId,
        }),
      );

      return {
        backLink,
        extraFields,
        loading,
        pageLoading,
        resource,
        saveFailed,
        saveFeedback,
        reviewWorkTitle$,
        reviewWorkDescription$,
        backToReportLabel$,
        feedbackNotSavedMessage$,
      };
    },
  };

</script>


<style lang="scss" scoped>

  .review-viewer {
    height: 80vh;
  }

  .save-error {
    color: var(--tokens-error);
  }

</style>
