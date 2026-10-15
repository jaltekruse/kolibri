import { Resource } from 'kolibri/apiResource';

/**
 * Learners' free-text answers to the prompts on a lesson resource.
 * Listing requires `lesson_id` and `contentnode_id` params: learners get their own
 * answers, coaches get the answers of the learners they coach.
 */
export default new Resource({
  name: 'lessonresponse',
  namespace: 'kolibri.plugins.lesson_responses',
  /**
   * Save the current learner's answers, and optionally submit them.
   * @param {object} options
   * @param {string} options.lessonId
   * @param {string} options.contentnodeId
   * @param {Object<string, string>} options.answers - Answer text keyed by prompt id
   * @param {boolean} [options.submit=false] - Whether to submit the answers
   * @returns {Promise<object[]>} The learner's saved answers
   */
  async saveAnswers({ lessonId, contentnodeId, answers, submit = false }) {
    const response = await this.request({
      method: 'POST',
      action: 'save',
      data: {
        lesson_id: lessonId,
        contentnode_id: contentnodeId,
        answers,
        submit,
      },
    });
    return response.data;
  },
});
