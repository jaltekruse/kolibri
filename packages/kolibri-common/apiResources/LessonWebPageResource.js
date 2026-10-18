import { Resource } from 'kolibri/apiResource';

/**
 * Pages on the public web in lessons, which learners work from in the Free Math editor.
 * Each has a `title`, `url`, `instructions`, `problem_numbers` as the coach wrote them
 * (such as "1-10, 21-35 by 3") and, read-only, `problems`: those numbers one by one.
 * Filter by lesson with the `lesson` param. Coaches who can edit a lesson can change its
 * web pages; learners can read the web pages in active lessons assigned to them.
 */
export default new Resource({
  name: 'lessonwebpage',
  namespace: 'kolibri.plugins.lesson_responses',
});
