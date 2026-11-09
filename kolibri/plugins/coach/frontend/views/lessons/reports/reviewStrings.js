import { createTranslator } from 'kolibri/utils/i18n';

export const reviewStrings = createTranslator('LessonResourceReviewPageStrings', {
  reviewWorkTitle: {
    message: 'Review work: {title}',
    context: "Heading of the page where coaches review learners' work in a resource",
  },
  reviewWorkDescription: {
    message:
      'Review the work learners in this lesson have done in this resource and give them feedback. Learners see your feedback when they next open the resource.',
    context: "Description of the page where coaches review learners' work in a resource",
  },
  backToReportLabel: {
    message: 'Back to report',
    context: 'Link back to the report on learners in a lesson resource',
  },
  reviewWorkLabel: {
    message: 'Review work',
    context: "Button to open the page where coaches review learners' work in a resource",
  },
  feedbackNotSavedMessage: {
    message: 'Some feedback could not be saved. Please try again.',
    context: "Error shown when feedback given to learners couldn't be saved",
  },
});
