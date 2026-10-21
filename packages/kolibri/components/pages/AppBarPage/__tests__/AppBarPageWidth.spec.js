import { render, screen } from '@testing-library/vue';
import useKResponsiveWindow from 'kolibri-design-system/lib/composables/useKResponsiveWindow';
import AppBarPage from '../index';

jest.mock('kolibri-design-system/lib/composables/useKResponsiveWindow');
jest.mock('vue-router/composables', () => ({
  useRoute: jest.fn(() => ({ params: {}, query: {} })),
}));

function renderPage(props = {}) {
  render(AppBarPage, {
    props: { title: 'Lesson', ...props },
    slots: { default: '<p data-testid="page-content">Lesson resources</p>' },
  });
  // The page's content area holds whatever the page renders
  return screen.getByTestId('page-content').parentElement;
}

describe('AppBarPage width', () => {
  beforeAll(() => {
    useKResponsiveWindow.mockImplementation(() => ({ windowIsSmall: false }));
  });

  it('keeps content to a readable width', () => {
    expect(renderPage()).toHaveStyle({ maxWidth: '1064px' });
  });

  it('lets content use the whole width when asked to', () => {
    expect(renderPage({ fullWidth: true })).toHaveStyle({ maxWidth: '100%' });
  });
});
