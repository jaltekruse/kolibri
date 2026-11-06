<template>

  <section
    class="lesson-web-pages"
    :aria-labelledby="headingId"
  >
    <div class="header">
      <h2 :id="headingId">
        {{ webPagesLabel$() }}
      </h2>
      <KButton
        v-if="editable"
        :text="addWebPageAction$()"
        appearance="flat-button"
        icon="plus"
        @click="openModal(null)"
      />
    </div>

    <KCircularLoader v-if="loading" />
    <p
      v-else-if="loadError"
      role="alert"
    >
      {{ webPagesLoadError$() }}
    </p>
    <p
      v-else-if="!webPages.length"
      data-testid="no-web-pages"
    >
      {{ noWebPagesDescription$() }}
    </p>
    <ul
      v-else
      class="web-pages"
    >
      <li
        v-for="webPage in webPages"
        :key="webPage.id"
        class="web-page"
        :data-testid="`web-page-${webPage.id}`"
      >
        <div class="details">
          <KRouterLink
            :text="webPage.title"
            :to="reportRoute(webPage)"
          />
          <KExternalLink
            class="url"
            :href="webPage.url"
            :text="webPage.url"
            :openInNewTab="true"
          />
          <span class="problems">
            {{ problemsCountLabel$({ count: webPage.problems.length }) }}:
            {{ webPage.problem_numbers }}
          </span>
        </div>
        <div
          v-if="editable"
          class="actions"
        >
          <KButton
            :text="editAction$()"
            appearance="flat-button"
            @click="openModal(webPage)"
          />
          <KButton
            :text="removeAction$()"
            appearance="flat-button"
            @click="webPageToRemove = webPage"
          />
        </div>
      </li>
    </ul>

    <LessonWebPageModal
      v-if="modalOpen"
      :lessonId="lessonId"
      :webPage="webPageToEdit"
      @saved="handleSaved"
      @cancel="modalOpen = false"
    />
    <KModal
      v-if="webPageToRemove"
      :title="removeWebPageTitle$()"
      :submitText="removeAction$()"
      :cancelText="cancelAction$()"
      @submit="remove"
      @cancel="webPageToRemove = null"
    >
      <p>{{ removeWebPageDescription$({ title: webPageToRemove.title }) }}</p>
    </KModal>
  </section>

</template>


<script>

  import { getCurrentInstance, ref } from 'vue';
  import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
  import useSnackbar from 'kolibri/composables/useSnackbar';
  import LessonWebPageResource from 'kolibri-common/apiResources/LessonWebPageResource';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
  import { PageNames } from '../../../constants';
  import LessonWebPageModal from './LessonWebPageModal';

  /**
   * The pages from the web in a lesson, which learners see next to a math editor where
   * they show their work on the problems the coach listed. Coaches who can edit the
   * lesson can add, change and remove them.
   */
  export default {
    name: 'LessonWebPages',
    components: {
      LessonWebPageModal,
    },
    setup(props) {
      const headingId = `lesson-web-pages-${getCurrentInstance().uid}`;
      const webPages = ref([]);
      const loading = ref(true);
      const loadError = ref(null);
      const modalOpen = ref(false);
      // The web page being changed in the modal, or null when adding one
      const webPageToEdit = ref(null);
      const webPageToRemove = ref(null);
      const { createSnackbar } = useSnackbar();

      const {
        addWebPageAction$,
        noWebPagesDescription$,
        problemsCountLabel$,
        removeWebPageDescription$,
        removeWebPageTitle$,
        webPageSaveError$,
        webPagesLabel$,
        webPagesLoadError$,
      } = lessonResponsesStrings;
      const { cancelAction$, editAction$, removeAction$ } = coreStrings;

      async function load() {
        try {
          webPages.value = await LessonWebPageResource.list({ lesson: props.lessonId });
        } catch (error) {
          loadError.value = error;
        } finally {
          loading.value = false;
        }
      }

      function openModal(webPage) {
        webPageToEdit.value = webPage;
        modalOpen.value = true;
      }

      function handleSaved(saved) {
        modalOpen.value = false;
        const index = webPages.value.findIndex(webPage => webPage.id === saved.id);
        webPages.value =
          index === -1
            ? [...webPages.value, saved]
            : webPages.value.map(webPage => (webPage.id === saved.id ? saved : webPage));
      }

      async function remove() {
        const { id } = webPageToRemove.value;
        webPageToRemove.value = null;
        try {
          await LessonWebPageResource.delete(id);
          webPages.value = webPages.value.filter(webPage => webPage.id !== id);
        } catch (error) {
          createSnackbar(webPageSaveError$());
        }
      }

      function reportRoute(webPage) {
        return {
          name: PageNames.LESSON_WEB_PAGE_REPORT,
          params: { classId: props.classId, lessonId: props.lessonId, webPageId: webPage.id },
        };
      }

      load();

      return {
        headingId,
        loadError,
        loading,
        modalOpen,
        webPages,
        webPageToEdit,
        webPageToRemove,
        handleSaved,
        openModal,
        remove,
        reportRoute,
        addWebPageAction$,
        cancelAction$,
        editAction$,
        noWebPagesDescription$,
        problemsCountLabel$,
        removeAction$,
        removeWebPageDescription$,
        removeWebPageTitle$,
        webPagesLabel$,
        webPagesLoadError$,
      };
    },
    props: {
      classId: {
        type: String,
        required: true,
      },
      lessonId: {
        type: String,
        required: true,
      },
      // Whether the coach can add, change and remove web pages
      editable: {
        type: Boolean,
        default: false,
      },
    },
  };

</script>


<style lang="scss" scoped>

  .lesson-web-pages {
    margin-top: 32px;
  }

  .header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
  }

  .web-pages {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .web-page {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    padding: 12px 0;
    border-top: 1px solid var(--tokens-fineLine);
  }

  .details {
    display: flex;
    flex-direction: column;
    min-width: 0;

    > * {
      margin-bottom: 4px;
    }
  }

  .url {
    overflow-wrap: anywhere;
  }

  .problems {
    font-size: 14px;
    color: var(--tokens-annotation);
  }

</style>
