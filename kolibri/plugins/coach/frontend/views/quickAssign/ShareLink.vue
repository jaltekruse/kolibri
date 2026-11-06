<template>

  <div class="share-link">
    <span
      ref="linkText"
      class="link-text"
      data-testid="share-link"
    >{{ link }}</span>
    <KButton
      :text="copyLinkAction$()"
      appearance="raised-button"
      @click="copy"
    />
  </div>

</template>


<script>

  import { ref } from 'vue';
  import useSnackbar from 'kolibri/composables/useSnackbar';
  import { quickAssignStrings } from 'kolibri-common/strings/quickAssignStrings';

  /**
   * A quick assignment's link, with a button to copy it. Browsers only allow copying
   * from secure pages, so elsewhere the button selects the link for the coach to copy.
   */
  export default {
    name: 'ShareLink',
    setup(props) {
      const linkText = ref(null);
      const { createSnackbar } = useSnackbar();
      const { copyLinkAction$, linkCopiedMessage$ } = quickAssignStrings;

      async function copy() {
        if (navigator.clipboard) {
          await navigator.clipboard.writeText(props.link);
          createSnackbar(linkCopiedMessage$());
          return;
        }
        const range = document.createRange();
        range.selectNodeContents(linkText.value);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }

      return { linkText, copy, copyLinkAction$ };
    },
    props: {
      link: {
        type: String,
        required: true,
      },
    },
  };

</script>


<style lang="scss" scoped>

  .share-link {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    align-items: center;
  }

  .link-text {
    padding: 8px;
    font-family: monospace;
    word-break: break-all;
    background-color: var(--palette-grey-v100);
    border-radius: 4px;
  }

</style>
