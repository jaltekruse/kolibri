import { createTranslator } from 'kolibri/utils/i18n';

export const lessonResponsesStrings = createTranslator('LessonResponsesStrings', {
  questionsLabel: {
    message: 'Questions',
    context: 'Heading for the questions a coach wrote for learners to answer about a resource.',
  },
  questionsDescription: {
    message: 'Show your work for each question about this resource in the math editor.',
    context:
      'Instructions shown to learners above the math editor where they answer questions about a resource.',
  },
  mathEditorLabel: {
    message: 'Math editor for your answers',
    context:
      'Accessible name of the math editor where a learner shows their work on the questions about a resource.',
  },
  questionNumberLabel: {
    message: 'Question {number, number}',
    context: 'Label for one of the questions a coach wrote about a resource.',
  },
  savingStatus: {
    message: 'Saving…',
    context: "Shown while a learner's answers are being saved.",
  },
  savedStatus: {
    message: 'Answers saved',
    context: "Shown once a learner's answers have been saved.",
  },
  saveErrorStatus: {
    message: 'Your answers could not be saved. Check your connection and try again.',
    context: "Shown when a learner's answers could not be saved.",
  },
  loadErrorStatus: {
    message: 'Your answers could not be loaded. Check your connection and try again.',
    context: "Shown when a learner's saved answers could not be loaded.",
  },
  tryAgainAction: {
    message: 'Try again',
    context: "Button to retry saving a learner's answers after saving failed.",
  },
  submitAnswersAction: {
    message: 'Submit answers',
    context: 'Button for a learner to submit their answers to the coach.',
  },
  submitAnswersTitle: {
    message: 'Submit your answers?',
    context: 'Title of the dialog where a learner confirms submitting their answers.',
  },
  submitAnswersDescription: {
    message: 'You will not be able to change your answers after you submit them.',
    context: 'Explains to a learner that submitted answers cannot be changed.',
  },
  unansweredQuestionsWarning: {
    message:
      '{count, number} {count, plural, one {question has} other {questions have}} no answer.',
    context: 'Warns a learner, before they submit, how many questions they did not answer.',
  },
  submittedStatus: {
    message: 'Submitted',
    context: 'Status of answers that a learner has submitted to their coach.',
  },
  noAnswersYetStatus: {
    message: 'No learners have answered these questions yet.',
    context: 'Shown to a coach in place of the learner answers to grade, when there are none.',
  },
  // Coach strings
  editQuestionsAction: {
    message: 'Questions for learners',
    context:
      'Button for a coach to write questions that learners answer in their own words about a resource in a lesson.',
  },
  questionsCountLabel: {
    message: 'Questions ({count, number})',
    context:
      'Button for a coach to edit the questions learners answer about a resource in a lesson, showing how many there are.',
  },
  editQuestionsDescription: {
    message:
      'Learners show their work on these questions in a math editor while viewing this resource. You can refer to pages or sections of the resource.',
    context: 'Instructions for a coach writing questions about a resource in a lesson.',
  },
  addQuestionAction: {
    message: 'Add question',
    context: 'Button for a coach to add a question for learners to answer.',
  },
  removeQuestionAction: {
    message: 'Remove question {number, number}',
    context: 'Accessible label for the button that removes a question.',
  },
  learnerAnswersLabel: {
    message: 'Learner answers',
    context: "Heading for learners' answers to a coach's questions about a resource.",
  },
  learnerAnswersLoadError: {
    message: 'Learner answers could not be loaded. Refresh the page to try again.',
    context: "Shown to a coach when learners' answers to questions about a resource fail to load.",
  },
  gradingEditorLabel: {
    message: 'Math editor for grading learner answers',
    context:
      "Accessible name of the math editor where a coach grades learners' work on the questions about a resource, grouped by similar answers.",
  },
  // Web pages in lessons
  webPagesLabel: {
    message: 'Web pages',
    context:
      'Heading for pages from the web, such as practice problems on another site, that a lesson asks learners to work from.',
  },
  webPagesDescription: {
    message:
      'Learners see each page next to a math editor, where they show their work on the problems you list.',
    context: "Explains web pages in a lesson to a coach, above the lesson's list of web pages.",
  },
  noWebPagesDescription: {
    message: 'This lesson has no web pages.',
    context: 'Shown to a coach in place of the list of web pages in a lesson, when there are none.',
  },
  webPagesLoadError: {
    message: 'Web pages could not be loaded. Refresh the page to try again.',
    context: 'Shown when the web pages in a lesson fail to load.',
  },
  addWebPageAction: {
    message: 'Add web page',
    context: 'Button for a coach to add a page from the web to a lesson.',
  },
  editWebPageTitle: {
    message: 'Edit web page',
    context: 'Title of the dialog where a coach changes a web page in a lesson.',
  },
  webPageUrlLabel: {
    message: 'Web address',
    context: 'Label for the box where a coach enters the address (URL) of a page on the web.',
  },
  webPageUrlInvalid: {
    message: 'Enter a web address that starts with http:// or https://',
    context: 'Shown when the web address a coach entered for a web page is not usable.',
  },
  webPageEmbedHint: {
    message:
      'Some websites do not allow their pages to be shown inside other websites. Learners can always open the page in a new tab.',
    context: 'Note for a coach adding a web page to a lesson, below the web address.',
  },
  instructionsLabel: {
    message: 'Instructions',
    context:
      'Label for what a coach tells learners to do on a web page, such as which problems to solve.',
  },
  problemNumbersLabel: {
    message: 'Problem numbers',
    context:
      'Label for the box where a coach lists the problems on a web page that learners show their work on.',
  },
  problemNumbersHint: {
    message: 'Use commas between problems and ranges, for example: 1-10, 21-35 by 3',
    context:
      'Explains how a coach lists problems: "21-35 by 3" means every third problem from 21 to 35. Keep the example as written.',
  },
  problemNumbersInvalid: {
    message:
      'Check the problem numbers. Ranges like 21-35 must go up, and there can be at most 100 problems.',
    context: 'Shown when the problem numbers a coach listed for a web page are not usable.',
  },
  problemsCountLabel: {
    message: '{count, number} {count, plural, one {problem} other {problems}}',
    context: 'How many problems learners show their work on for a web page.',
  },
  problemsListLabel: {
    message: 'Problems: {problems}',
    context: 'The problems learners show their work on for a web page, as the coach listed them.',
  },
  webPageSaveError: {
    message: 'The web page could not be saved',
    context: 'Shown when saving a web page in a lesson fails.',
  },
  removeWebPageTitle: {
    message: 'Remove web page',
    context: 'Title of the dialog where a coach confirms removing a web page from a lesson.',
  },
  removeWebPageDescription: {
    message: "Learners will no longer see '{title}' in this lesson.",
    context: 'Asks a coach to confirm removing a web page from a lesson.',
  },
  openWebPageAction: {
    message: 'Open page in a new tab',
    context: 'Link that opens a web page from a lesson in a new browser tab.',
  },
  webPageNotShowingHint: {
    message: 'If the page does not appear, open it in a new tab.',
    context:
      'Shown to learners above a web page from a lesson, since some websites do not allow being shown inside Kolibri.',
  },
});
