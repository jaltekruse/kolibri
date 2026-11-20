import { render, screen, fireEvent } from '@testing-library/vue';
import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
import LessonResourcesTable from '../tables/LessonResourcesTable';

const { questionsCountLabel$ } = lessonResponsesStrings;

const ENTRIES = [
  { node_id: 'reading-id', title: 'Photosynthesis reading', kind: 'document', promptCount: 2 },
  { node_id: 'exercise-id', title: 'Photosynthesis practice', kind: 'exercise', promptCount: 0 },
];

function renderTable(editable = true) {
  return render(LessonResourcesTable, {
    props: { entries: ENTRIES, editable },
    store: { modules: { classSummary: { namespaced: true, state: { name: 'Class' } } } },
  });
}

describe('LessonResourcesTable', () => {
  it("opens a resource's questions from its row", async () => {
    const { emitted } = renderTable();
    await fireEvent.click(screen.getByRole('button', { name: questionsCountLabel$({ count: 2 }) }));
    expect(emitted().editPrompts[0][0].node_id).toBe('reading-id');
  });

  it('offers questions only for resources that are not exercises', () => {
    renderTable();
    // The exercise row has no questions, so its button would read "Questions (0)"
    expect(
      screen.queryByRole('button', { name: questionsCountLabel$({ count: 0 }) }),
    ).not.toBeInTheDocument();
  });

  it('does not offer questions when the lesson cannot be edited', () => {
    renderTable(false);
    expect(
      screen.queryByRole('button', { name: questionsCountLabel$({ count: 2 }) }),
    ).not.toBeInTheDocument();
  });
});
