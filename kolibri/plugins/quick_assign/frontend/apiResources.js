import { Resource } from 'kolibri/apiResource';

/**
 * Quick assignment links, by their token. Retrieving one gives the assignment's `title`
 * and `coach_name`, whether it `is_open` to new students, `is_coach` when the coach who
 * can see the work opened it, and `learner`: who this browser joins as, if anyone, with
 * their `full_name` and whether they are `is_signed_in`.
 */
export const JoinLinkResource = new Resource({
  name: 'joinlink',
  namespace: 'kolibri.plugins.quick_assign',
  /**
   * Join the assignment and sign in.
   * @param {string} token - The token from the link
   * @param {string} [fullName] - The full name of a new student; leave out to join as the
   * student this browser is signed in or remembered as
   * @returns {Promise<object>} Where the assignment is: its `classroom_id` and `lesson_id`,
   * and a `web_page_id` or `contentnode_id` to open straight away
   */
  async join(token, fullName) {
    const response = await this.request({
      method: 'POST',
      action: 'join',
      routeParams: token,
      data: fullName ? { full_name: fullName } : {},
    });
    return response.data;
  },
});
