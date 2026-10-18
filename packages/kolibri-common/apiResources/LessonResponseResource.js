import { Resource } from 'kolibri/apiResource';

/**
 * Learners' answers to the prompts on a lesson resource, each a base64 encoded Free Math
 * document that also holds the coach's grading.
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
   * @param {{[promptId: string]: string}} options.answers - Free Math documents keyed by
   * prompt id
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
  /**
   * Save a coach's grading of learners' answers.
   * @param {object} options - The graded answers and where they belong
   * @param {string} options.lessonId - The lesson the resource is in
   * @param {string} options.contentnodeId - The resource the prompts are about
   * @param {{[learnerId: string]: {[promptId: string]: string}}} options.grades - For each
   * learner, the Free Math documents of their answers with the coach's grading in them,
   * keyed by prompt id
   * @returns {Promise} Resolves once the grading is saved
   */
  grade({ lessonId, contentnodeId, grades }) {
    return this.request({
      method: 'POST',
      action: 'grade',
      data: {
        lesson_id: lessonId,
        contentnode_id: contentnodeId,
        grades,
      },
    });
  },
});
