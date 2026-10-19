import urls from 'kolibri/urls';

/**
 * The address in Learn of what a student opens after joining a quick assignment: its
 * web page or its one exercise, or else its lesson.
 * @param {object} destination - Where the assignment is, as the join endpoint gives it
 * @param {string} destination.classroom_id - The class its lesson is in
 * @param {string} destination.lesson_id - Its lesson
 * @param {string|null} destination.web_page_id - Its web page, to open straight away
 * @param {string|null} destination.contentnode_id - Its one exercise, to open straight away
 * @returns {string} The address
 */
export default function assignmentUrl({
  classroom_id: classId,
  lesson_id: lessonId,
  web_page_id: webPageId,
  contentnode_id: contentNodeId,
}) {
  const learn = urls['kolibri:kolibri.plugins.learn:learn']();
  const lesson = `/classes/${classId}/lesson/${lessonId}`;
  if (webPageId) {
    return `${learn}#${lesson}/webpage/${webPageId}`;
  }
  if (contentNodeId) {
    // As Learn links to a resource from a lesson, so its back button returns there
    const query = new URLSearchParams({
      prevName: 'LESSON_PLAYLIST',
      prevParams: encodeURI(JSON.stringify({ classId, lessonId })),
    });
    return `${learn}#/topics/c/${contentNodeId}?${query}`;
  }
  return `${learn}#${lesson}`;
}
