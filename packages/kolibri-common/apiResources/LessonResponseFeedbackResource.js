import { Resource } from 'kolibri/apiResource';

/**
 * Coach feedback on a learner's answers to the prompts on a lesson resource.
 * Listing requires `lesson_id` and `contentnode_id` params.
 */
export default new Resource({
  name: 'lessonresponsefeedback',
  namespace: 'kolibri.plugins.lesson_responses',
});
