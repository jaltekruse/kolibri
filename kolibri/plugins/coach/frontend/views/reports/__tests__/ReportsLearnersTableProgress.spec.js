import { render, screen, within } from '@testing-library/vue';
import VueRouter from 'vue-router';
import { STATUSES } from '../../../modules/classSummary/constants';
import ReportsLearnersTable from '../../common/tables/ReportsLearnersTable';

jest.mock('kolibri/utils/serverClock', () => ({
  now: () => new Date('2019-05-05T11:00:00Z'),
}));

function entry(id, name, statusObj) {
  return {
    id,
    name,
    groups: [],
    link: `#/learners/${id}`,
    statusObj: { learner_id: id, content_id: 'a97', time_spent: 60, ...statusObj },
  };
}

function renderTable(entries) {
  return render(ReportsLearnersTable, {
    props: { entries, showGroupsColumn: false },
    routes: new VueRouter(),
  });
}

// each test shows a single learner, in the table's only entry
function learnerRow() {
  return screen.getByTestId('entry');
}

describe('ReportsLearnersTable progress', () => {
  it('shows the progress of a learner who has started a resource', () => {
    renderTable([entry('a5d', 'learner2', { status: STATUSES.started, progress: 0.25 })]);
    expect(within(learnerRow()).getByTestId('progress-percent')).toHaveTextContent('25%');
  });

  it("doesn't show progress for a resource the learner has completed", () => {
    renderTable([entry('d4b', 'learner1', { status: STATUSES.completed, progress: 1 })]);
    expect(within(learnerRow()).queryByTestId('progress-percent')).not.toBeInTheDocument();
  });

  it("doesn't show progress when there is none", () => {
    renderTable([entry('e7c', 'learner3', { status: STATUSES.started })]);
    expect(within(learnerRow()).queryByTestId('progress-percent')).not.toBeInTheDocument();
  });
});
