<template>

  <ImmersivePage
    :route="lessonRoute"
    :appBarTitle="webPage ? webPage.title : ''"
    :loading="loading"
    icon="back"
  >
    <template #default="{ pageContentHeight }">
      <p
        v-if="loadError"
        role="alert"
      >
        {{ webPagesLoadError$() }}
      </p>
      <div
        v-else-if="webPage"
        class="layout"
        :class="{ 'side-by-side': windowIsLarge }"
        :style="windowIsLarge ? { height: `${pageContentHeight}px` } : {}"
      >
        <section
          class="web-page"
          :aria-label="webPage.title"
        >
          <p class="web-page-bar">
            <span>{{ webPageNotShowingHint$() }}</span>
            <KExternalLink
              :href="webPage.url"
              :text="openWebPageAction$()"
              :openInNewTab="true"
            />
          </p>
          <!-- The page comes from another website: it may run its own scripts and forms,
               but cannot navigate Kolibri, and is not told which Kolibri page framed it. -->
          <iframe
            class="web-page-frame"
            :src="webPage.url"
            :title="webPage.title"
            :sandbox="SANDBOX"
            referrerpolicy="no-referrer"
          ></iframe>
        </section>
        <LessonResponsesPanel
          class="responses"
          :lessonId="lessonId"
          :itemId="webPage.id"
          :problems="problems"
          :instructions="webPage.instructions"
          :title="webPage.title"
        />
      </div>
    </template>
  </ImmersivePage>

</template>


<script>

  import { computed, ref } from 'vue';
  import { useRoute } from 'vue-router/composables';
  import useKResponsiveWindow from 'kolibri-design-system/lib/composables/useKResponsiveWindow';
  import ImmersivePage from 'kolibri/components/pages/ImmersivePage';
  import usePageTitle from 'kolibri/composables/usePageTitle';
  import LessonWebPageResource from 'kolibri-common/apiResources/LessonWebPageResource';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
  import { ClassesPageNames } from '../../constants';
  import LessonResponsesPanel from './LessonResponsesPanel';

  // Everything a page from another website needs, but not navigating the page around it
  const SANDBOX = [
    'allow-scripts',
    'allow-same-origin',
    'allow-forms',
    'allow-popups',
    'allow-popups-to-escape-sandbox',
  ].join(' ');

  /**
   * A page from the web in a lesson, next to the math editor where learners show their
   * work on the problems the coach listed. Side by side on large windows, with the
   * editor below the page otherwise.
   */
  export default {
    name: 'LessonWebPagePage',
    components: {
      ImmersivePage,
      LessonResponsesPanel,
    },
    setup() {
      const route = useRoute();
      const { classId, lessonId, webPageId } = route.params;
      const { windowIsLarge } = useKResponsiveWindow();
      const webPage = ref(null);
      const loading = ref(true);
      const loadError = ref(null);

      // Problems are numbered as the coach listed them
      const problems = computed(() =>
        webPage.value.problems.map(number => ({ key: number, number, prompt: '' })),
      );

      const lessonRoute = {
        name: ClassesPageNames.LESSON_PLAYLIST,
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

      usePageTitle(() => webPage.value?.title, { hasVisibleHeading: false });

      load();

      const { openWebPageAction$, webPageNotShowingHint$, webPagesLoadError$ } =
        lessonResponsesStrings;

      return {
        SANDBOX,
        lessonId,
        lessonRoute,
        loadError,
        loading,
        problems,
        webPage,
        windowIsLarge,
        openWebPageAction$,
        webPageNotShowingHint$,
        webPagesLoadError$,
      };
    },
  };

</script>


<style lang="scss" scoped>

  .web-page {
    display: flex;
    flex-direction: column;
    background-color: var(--tokens-surface);
  }

  .web-page-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    align-items: center;
    justify-content: space-between;
    padding: 8px 16px;
    margin: 0;
    font-size: 14px;
    color: var(--tokens-annotation);
  }

  .web-page-frame {
    display: block;
    width: 100%;
    height: 70vh;
    border: 0;
    border-top: 1px solid var(--tokens-fineLine);
  }

  .side-by-side {
    display: flex;

    .web-page {
      flex: 1 1 50%;
      min-width: 0;
    }

    .web-page-frame {
      flex: 1 1 auto;
      height: auto;
    }

    .responses {
      flex: 1 1 50%;
      min-width: 0;
      overflow-y: auto;
      border-left: 1px solid var(--tokens-fineLine);
    }
  }

</style>
