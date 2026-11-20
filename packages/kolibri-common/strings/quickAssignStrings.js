import { createTranslator } from 'kolibri/utils/i18n';

export const quickAssignStrings = createTranslator('QuickAssignStrings', {
  // For coaches
  quickAssignAction: {
    message: 'Quick assign',
    context:
      'Button for a coach to make an assignment that anyone with its link can join, without setting up a class first.',
  },
  quickAssignDescription: {
    message:
      'Make an assignment and share its link. Students join by typing their name, so there is no class to set up and no passwords to manage.',
    context: 'Explains quick assignments at the top of the page where a coach makes them.',
  },
  whatToAssignLabel: {
    message: 'What to assign',
    context: 'Label for the choice between exercises and Free Math work on a web page.',
  },
  exercisesOption: {
    message: 'Exercises from the library',
    context: 'Choice for a quick assignment of auto-graded exercises, such as Khan Academy ones.',
  },
  freeMathOption: {
    message: 'Problems from a web page, worked in Free Math',
    context:
      'Choice for a quick assignment where students show their work in the Free Math editor on problems from a web page.',
  },
  searchExercisesLabel: {
    message: 'Search for exercises',
    context: 'Label for the box where a coach searches the library for exercises to assign.',
  },
  noExercisesFound: {
    message: 'No exercises match your search',
    context: 'Shown when a search of the library finds no exercises.',
  },
  exerciseSearchError: {
    message: 'The library could not be searched',
    context: 'Shown when searching the library for exercises fails.',
  },
  addAction: {
    message: 'Add',
    context: 'Button that adds an exercise found in the library to a quick assignment.',
  },
  addExerciseAction: {
    message: 'Add {title}',
    context:
      'What screen readers say for the button that adds an exercise found in the library to a quick assignment.',
  },
  removeExerciseAction: {
    message: 'Remove {title}',
    context: 'Button that removes an exercise from a quick assignment before it is made.',
  },
  chosenExercisesLabel: {
    message: 'Exercises in this assignment',
    context: 'Heading above the exercises a coach chose for a quick assignment.',
  },
  chooseExercisesHint: {
    message: 'Search the library and add at least one exercise.',
    context: 'Shown when a coach has not chosen any exercises for a quick assignment yet.',
  },
  assignmentTitleLabel: {
    message: 'Assignment title',
    context: 'Label for the box where a coach names a quick assignment.',
  },
  createLinkAction: {
    message: 'Create link',
    context: 'Button that makes a quick assignment and its link.',
  },
  createError: {
    message: 'The assignment could not be made',
    context: 'Shown when making a quick assignment fails.',
  },
  linkReadyMessage: {
    message: "'{title}' is ready. Share this link with your students:",
    context: 'Shown with the link once a coach makes a quick assignment.',
  },
  copyLinkAction: {
    message: 'Copy link',
    context: 'Button that copies a quick assignment link so a coach can paste it elsewhere.',
  },
  linkCopiedMessage: {
    message: 'Link copied',
    context: 'Shown briefly after a coach copies a quick assignment link.',
  },
  yourQuickAssignmentsLabel: {
    message: 'Your quick assignments',
    context: 'Heading above the list of quick assignments a coach made.',
  },
  noQuickAssignments: {
    message: 'You have not made any quick assignments yet.',
    context: 'Shown in place of the list of quick assignments when a coach has none.',
  },
  quickAssignmentsLoadError: {
    message: 'Your quick assignments could not be loaded',
    context: 'Shown when the list of quick assignments fails to load.',
  },
  joinedCountLabel: {
    message: '{count, number} {count, plural, one {student} other {students}} joined',
    context: 'How many students joined a quick assignment through its link.',
  },
  linkOpenLabel: {
    message: 'Anyone with the link can join',
    context:
      'Switch for whether new students can join a quick assignment. Students who already joined keep their access.',
  },
  viewResultsAction: {
    message: 'View results',
    context: "Link to the report of students' work on a quick assignment.",
  },
  quickAssignClassName: {
    message: '{name} - quick assignments',
    context:
      "Name of the class Kolibri makes to hold a coach's quick assignments. 'name' is the coach's full name.",
  },
  // For students opening a link
  fromCoachLabel: {
    message: 'From {name}',
    context: 'Says which teacher shared the assignment a student is joining.',
  },
  fullNameHint: {
    message: 'Type your full name. Your teacher will see it with your work.',
    context: 'Shown to a student joining an assignment, below the box for their name.',
  },
  startAction: {
    message: 'Start',
    context: 'Button a student presses after typing their name, to join an assignment.',
  },
  continueAsAction: {
    message: 'Continue as {name}',
    context: 'Button for a student who joined from this browser before, to carry on as themselves.',
  },
  notYouAction: {
    message: 'I am not {name}',
    context:
      'Button for someone using a browser another student joined from, such as a shared computer, to join as themselves.',
  },
  linkClosedMessage: {
    message: 'This assignment is not taking new students. Ask your teacher about it.',
    context: 'Shown to a student opening the link of an assignment their teacher closed.',
  },
  coachViewingLinkMessage: {
    message:
      'This is the link for your students. To try it as a student, open it in a private browser window.',
    context: 'Shown to the coach who made an assignment when they open its link.',
  },
  linkNotWorkingMessage: {
    message: 'This link does not work. Check it with your teacher.',
    context: 'Shown when someone opens an assignment link that does not exist.',
  },
  joinError: {
    message: 'Something went wrong. Try again.',
    context: 'Shown when joining an assignment fails.',
  },
});
