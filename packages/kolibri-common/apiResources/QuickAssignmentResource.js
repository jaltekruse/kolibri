import { Resource } from 'kolibri/apiResource';

/**
 * The quick assignments the current coach made: lessons anyone with the `link` can join
 * by typing their name. Each has the lesson's `id`, `title`, `classroom_id` and
 * `resources`, a `web_page_id` for Free Math work on a web page, `learner_count` (how
 * many joined) and `is_open` (whether new students can still join), which can be changed.
 *
 * Create one with a `title`, `classroom_name` (for the coach's quick assignments class, if
 * it is their first) and either `exercise_ids` or a `web_page` with `url`, `instructions`
 * and `problem_numbers`.
 */
export default new Resource({
  name: 'quickassignment',
  namespace: 'kolibri.plugins.quick_assign',
});
