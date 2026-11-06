<template>

  <iframe
    ref="frame"
    class="free-math-frame"
    :src="src"
    :title="title"
  ></iframe>

</template>


<script>

  import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
  import urls from 'kolibri/urls';

  const SOURCE = 'free-math';
  const HOST_SOURCE = 'free-math-host';
  // How long to wait for Free Math to send pending work before giving up on it
  const FLUSH_TIMEOUT = 5000;

  /**
   * The Free Math editor, served by the lesson_responses plugin, in an iframe.
   * Free Math's embedded mode sends messages that this emits as events, and receives
   * the work to show with `send`. See Free Math's src/Embedded.js for the messages.
   */
  export default {
    name: 'FreeMathFrame',
    setup(props, { emit }) {
      const frame = ref(null);
      const src = computed(
        () =>
          `${urls['kolibri:kolibri.plugins.lesson_responses:free_math']()}?embedded=${props.mode}`,
      );

      let requestCount = 0;
      const pendingFlushes = new Map();

      /**
       * Send a message to Free Math.
       * @param {string} type - The message type, such as 'load-student'
       * @param {object} [payload] - The rest of the message
       */
      function send(type, payload = {}) {
        frame.value.contentWindow.postMessage(
          { ...payload, type, source: HOST_SOURCE },
          window.location.origin,
        );
      }

      /**
       * Ask Free Math to send any work it has not sent yet, as a `save` event.
       * @returns {Promise} Resolves once that work has been sent, or Free Math did not answer
       */
      function flush() {
        requestCount += 1;
        const requestId = requestCount;
        return new Promise(resolve => {
          const timeout = setTimeout(() => {
            pendingFlushes.delete(requestId);
            resolve();
          }, FLUSH_TIMEOUT);
          pendingFlushes.set(requestId, () => {
            clearTimeout(timeout);
            resolve();
          });
          send('flush', { requestId });
        });
      }

      function handleMessage(event) {
        const message = event.data;
        if (
          !frame.value ||
          event.source !== frame.value.contentWindow ||
          event.origin !== window.location.origin ||
          message?.source !== SOURCE
        ) {
          return;
        }
        if (message.type === 'ready') {
          emit('ready');
        } else if (message.type === 'save') {
          emit('save', message.answers);
        } else if (message.type === 'flushed' && pendingFlushes.has(message.requestId)) {
          pendingFlushes.get(message.requestId)();
          pendingFlushes.delete(message.requestId);
        } else if (message.type === 'save-grades') {
          emit('saveGrades', message.grades, ok =>
            send('save-grades-result', { requestId: message.requestId, ok }),
          );
        }
      }

      onMounted(() => window.addEventListener('message', handleMessage));
      onBeforeUnmount(() => window.removeEventListener('message', handleMessage));

      return {
        frame,
        src,
        // Called by the parent component, through a template ref
        // eslint-disable-next-line vue/no-unused-properties
        flush,
        // eslint-disable-next-line vue/no-unused-properties
        send,
      };
    },
    props: {
      // 'student' to work on problems, 'grader' to grade a class's work on them
      mode: {
        type: String,
        required: true,
        validator: value => ['student', 'grader'].includes(value),
      },
      // Accessible name of the frame
      title: {
        type: String,
        required: true,
      },
    },
    emits: ['ready', 'save', 'saveGrades'],
  };

</script>


<style lang="scss" scoped>

  .free-math-frame {
    display: block;
    width: 100%;
    border: 0;
  }

</style>
