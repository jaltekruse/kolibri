import { createTranslator } from 'kolibri/utils/i18n';

export const lessonResponsesStrings = createTranslator('LessonResponsesStrings', {
  questionsLabel: {
    message: 'Questions',
    context: 'Heading for the questions a coach wrote for learners to answer about a resource.',
  },
  questionsDescription: {
    message: 'Answer these questions about this resource in your own words.',
    context: 'Instructions shown to learners above the questions they answer about a resource.',
  },
  questionNumberLabel: {
    message: 'Question {number, number}',
    context: 'Label for one of the questions a coach wrote about a resource.',
  },
  answerToQuestionLabel: {
    message: 'Answer to question {number, number}',
    context: 'Label for the box where a learner types their answer to a question.',
  },
  noAnswerLabel: {
    message: 'No answer',
    context: 'Shown in place of an answer when a learner did not answer a question.',
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
  inProgressStatus: {
    message: 'Not submitted yet',
    context: 'Status of answers that a learner has started but not submitted.',
  },
  notStartedStatus: {
    message: 'No answers yet',
    context: 'Status for a learner who has not answered any questions about a resource.',
  },
  coachFeedbackLabel: {
    message: 'Feedback from your coach',
    context: "Heading for a coach's feedback, shown to the learner.",
  },
  // Coach strings
  editQuestionsAction: {
    message: 'Questions for learners',
    context:
      'Button for a coach to write questions that learners answer in their own words about a resource in a lesson.',
  },
  editQuestionsDescription: {
    message:
      'Learners answer these questions in their own words while viewing this resource. You can refer to pages or sections of the resource.',
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
  addFeedbackAction: {
    message: 'Add feedback',
    context: "Button for a coach to give feedback on a learner's answers.",
  },
  editFeedbackAction: {
    message: 'Edit feedback',
    context: "Button for a coach to change their feedback on a learner's answers.",
  },
  overallFeedbackLabel: {
    message: 'Feedback on all answers',
    context: "Label for a coach's feedback on all of a learner's answers together.",
  },
  answerFeedbackLabel: {
    message: 'Feedback on this answer',
    context: "Label for a coach's feedback on one of a learner's answers.",
  },
  feedbackLabel: {
    message: 'Feedback',
    context: "Label for a coach's feedback on a learner's answers.",
  },
  feedbackSavedMessage: {
    message: 'Feedback saved',
    context: 'Confirmation shown after a coach saves feedback for a learner.',
  },
  feedbackSaveError: {
    message: 'Feedback could not be saved',
    context: 'Shown when saving feedback for a learner fails.',
  },
});
