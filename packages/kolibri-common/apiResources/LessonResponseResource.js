import { Resource } from 'kolibri/apiResource';

/**
 * Learners' answers to the prompts on a lesson item, each a base64 encoded Free Math
 * document that also holds the coach's grading. A lesson item is a lesson resource with
 * questions, identified by its contentnode_id, or a lesson web page, by its id.
 * Listing requires `lesson_id` and `item_id` params: learners get their own answers,
 * coaches get the answers of the learners they coach.
 */
export default new Resource({
  name: 'lessonresponse',
  namespace: 'kolibri.plugins.lesson_responses',
  /**
   * Save the current learner's answers, and optionally submit them.
   * @param {object} options - The answers to save and where they belong
   * @param {string} options.lessonId - The lesson the resource is in
   * @param {string} options.itemId - The lesson item the prompts are about
   * @param {{[promptId: string]: string}} options.answers - Free Math documents keyed by
   * prompt id
   * @param {boolean} [options.submit=false] - Whether to submit the answers
   * @returns {Promise<object[]>} The learner's saved answers
   */
  async saveAnswers({ lessonId, itemId, answers, submit = false }) {
    const response = await this.request({
      method: 'POST',
      action: 'save',
      data: {
        lesson_id: lessonId,
        item_id: itemId,
        answers,
        submit,
      },
    });
    return response.data;
  },
  /**
   * Save a coach's grading of learners' answers.
   * @param {object} options - The graded answers and where they belong
   * @param {string} options.lessonId - The lesson the resource is in
   * @param {string} options.itemId - The lesson item the prompts are about
   * @param {{[learnerId: string]: {[promptId: string]: string}}} options.grades - For each
   * learner, the Free Math documents of their answers with the coach's grading in them,
   * keyed by prompt id
   * @returns {Promise} Resolves once the grading is saved
   */
  grade({ lessonId, itemId, grades }) {
    return this.request({
      method: 'POST',
      action: 'grade',
      data: {
        lesson_id: lessonId,
        item_id: itemId,
        grades,
      },
    });
  },
});
