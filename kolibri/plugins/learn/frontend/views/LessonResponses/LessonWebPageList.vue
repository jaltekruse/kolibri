<template>

  <section
    class="lesson-web-page-list"
    :aria-labelledby="headingId"
  >
    <h2 :id="headingId">
      {{ webPagesLabel$() }}
    </h2>
    <ul class="web-pages">
      <li
        v-for="webPage in webPages"
        :key="webPage.id"
        class="web-page"
        :data-testid="`web-page-${webPage.id}`"
      >
        <KRouterLink
          class="title"
          :text="webPage.title"
          :to="webPageRoute(webPage)"
        />
        <span class="problems">
          {{ problemsCountLabel$({ count: webPage.problems.length }) }}
        </span>
        <p
          v-if="webPage.instructions"
          class="instructions"
        >
          <span class="multiline-text">{{ webPage.instructions }}</span>
        </p>
      </li>
    </ul>
  </section>

</template>


<script>

  import { getCurrentInstance } from 'vue';
  import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
  import { ClassesPageNames } from '../../constants';

  /**
   * Links to the pages from the web in a lesson, which learners work from in the math
   * editor.
   */
  export default {
    name: 'LessonWebPageList',
    setup(props) {
      const headingId = `lesson-web-pages-${getCurrentInstance().uid}`;

      function webPageRoute(webPage) {
        return {
          name: ClassesPageNames.LESSON_WEB_PAGE,
          params: { classId: props.classId, lessonId: props.lessonId, webPageId: webPage.id },
        };
      }

      const { problemsCountLabel$, webPagesLabel$ } = lessonResponsesStrings;

      return { headingId, webPageRoute, problemsCountLabel$, webPagesLabel$ };
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
      webPages: {
        type: Array,
        required: true,
      },
    },
  };

</script>


<style lang="scss" scoped>

  .lesson-web-page-list {
    margin-top: 24px;
  }

  .web-pages {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .web-page {
    padding: 16px;
    margin-bottom: 16px;
    background-color: var(--tokens-surface);
    border-radius: 4px;
  }

  .title {
    margin-right: 16px;
    font-size: 18px;
    font-weight: bold;
  }

  .problems {
    color: var(--tokens-annotation);
  }

  .instructions {
    margin-bottom: 0;
  }

  .multiline-text {
    white-space: pre-wrap;
  }

</style>
