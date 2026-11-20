import JoinPage from './views/JoinPage';

export default [
  {
    // The token from an assignment's link
    path: '/:token?',
    name: 'JOIN',
    component: JoinPage,
    props: true,
  },
];
