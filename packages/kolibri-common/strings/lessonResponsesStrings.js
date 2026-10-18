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
});
