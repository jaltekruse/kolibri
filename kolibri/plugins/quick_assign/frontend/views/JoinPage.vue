<template>

  <div class="join-page">
    <main class="card">
      <KCircularLoader v-if="loading" />
      <p
        v-else-if="!link"
        role="alert"
      >
        {{ linkNotWorkingMessage$() }}
      </p>
      <template v-else>
        <h1 class="title">{{ link.title }}</h1>
        <p class="coach">{{ fromCoachLabel$({ name: link.coach_name }) }}</p>

        <template v-if="link.is_coach">
          <p>{{ coachViewingLinkMessage$() }}</p>
          <KExternalLink
            :href="quickAssignPageUrl"
            :text="quickAssignAction$()"
          />
        </template>

        <template v-else-if="link.learner && !choosingName">
          <KButton
            primary
            :text="continueAsAction$({ name: link.learner.full_name })"
            :disabled="joining"
            @click="join()"
          />
          <KButton
            appearance="flat-button"
            :text="notYouAction$({ name: link.learner.full_name })"
            :disabled="joining"
            @click="chooseName"
          />
        </template>

        <p
          v-else-if="!link.is_open"
          data-testid="link-closed"
        >
          {{ linkClosedMessage$() }}
        </p>

        <form
          v-else
          @submit.prevent="start"
        >
          <KTextbox
            ref="nameTextbox"
            v-model="fullName"
            class="name"
            :label="fullNameLabel$()"
            :maxlength="120"
            :invalid="!fullNameValid"
            :invalidText="requiredFieldError$()"
            :showInvalidText="triedToStart"
            :disabled="joining"
            :autofocus="true"
            autocomplete="name"
          />
          <p class="hint">{{ fullNameHint$() }}</p>
          <KButton
            primary
            type="submit"
            :text="startAction$()"
            :disabled="joining"
          />
        </form>

        <p
          v-if="joinFailure"
          role="alert"
          class="error"
        >
          {{ joinFailure === 'closed' ? linkClosedMessage$() : joinError$() }}
        </p>
      </template>
    </main>
  </div>

</template>


<script>

  import { computed, nextTick, ref } from 'vue';
  import urls from 'kolibri/urls';
  import usePageTitle from 'kolibri/composables/usePageTitle';
  import redirectBrowser from 'kolibri/utils/redirectBrowser';
  import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
  import { quickAssignStrings } from 'kolibri-common/strings/quickAssignStrings';
  import { JoinLinkResource } from '../apiResources';
  import assignmentUrl from '../assignmentUrl';

  /**
   * Where someone sent a quick assignment's link joins it, by typing their name, or as
   * the student their browser joined as before. Then they go straight to the work.
   */
  export default {
    name: 'JoinPage',
    setup(props) {
      const link = ref(null);
      const loading = ref(true);
      const fullName = ref('');
      const fullNameValid = computed(() => fullName.value.trim() !== '');
      const triedToStart = ref(false);
      // Whether someone other than the remembered student is joining
      const choosingName = ref(false);
      const joining = ref(false);
      // 'closed' when the coach stopped new students joining, or 'error'
      const joinFailure = ref(null);
      const nameTextbox = ref(null);

      const quickAssignPageUrl = `${urls['kolibri:kolibri.plugins.coach:coach']()}#/quick-assign`;

      async function load() {
        try {
          link.value = props.token ? await JoinLinkResource.retrieve(props.token) : null;
        } catch (error) {
          link.value = null;
        } finally {
          loading.value = false;
        }
      }

      /**
       * Join, as a new student with this name, or without one as the student this
       * browser is signed in or remembered as.
       * @param {string} [name] - The new student's full name
       */
      async function join(name) {
        if (name !== undefined && !fullNameValid.value) {
          return;
        }
        joining.value = true;
        joinFailure.value = null;
        try {
          const destination = await JoinLinkResource.join(props.token, name);
          redirectBrowser(assignmentUrl(destination));
        } catch (error) {
          joinFailure.value = error.response?.status === 403 ? 'closed' : 'error';
          joining.value = false;
        }
      }

      function start() {
        triedToStart.value = true;
        join(fullName.value.trim());
      }

      async function chooseName() {
        choosingName.value = true;
        await nextTick();
        nameTextbox.value?.focus();
      }

      usePageTitle(() => link.value?.title, { hasVisibleHeading: true });

      load();

      const {
        coachViewingLinkMessage$,
        continueAsAction$,
        fromCoachLabel$,
        fullNameHint$,
        joinError$,
        linkClosedMessage$,
        linkNotWorkingMessage$,
        notYouAction$,
        quickAssignAction$,
        startAction$,
      } = quickAssignStrings;
      const { fullNameLabel$, requiredFieldError$ } = coreStrings;

      return {
        choosingName,
        fullName,
        fullNameValid,
        joinFailure,
        joining,
        link,
        loading,
        nameTextbox,
        quickAssignPageUrl,
        triedToStart,
        chooseName,
        join,
        start,
        coachViewingLinkMessage$,
        continueAsAction$,
        fromCoachLabel$,
        fullNameHint$,
        fullNameLabel$,
        joinError$,
        linkClosedMessage$,
        linkNotWorkingMessage$,
        notYouAction$,
        quickAssignAction$,
        requiredFieldError$,
        startAction$,
      };
    },
    props: {
      token: {
        type: String,
        default: '',
      },
    },
  };

</script>


<style lang="scss" scoped>

  .join-page {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 16px;
    background-color: var(--palette-grey-v100);
  }

  .card {
    display: flex;
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
    width: 100%;
    max-width: 480px;
    padding: 32px;
    background-color: var(--tokens-surface);
    border-radius: 8px;
  }

  .title {
    margin: 0;
  }

  .coach,
  .hint {
    margin: 0;
    color: var(--tokens-annotation);
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
    width: 100%;
  }

  .name {
    align-self: stretch;
  }

  .error {
    margin: 0;
    color: var(--tokens-error);
  }

</style>
