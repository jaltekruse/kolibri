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
   * @param {object} options - The answers to save and where they belong
   * @param {string} options.lessonId - The lesson the resource is in
   * @param {string} options.contentnodeId - The resource the prompts are about
   * @param {{[promptId: string]: string}} options.answers - Answer text keyed by prompt id
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
