import { render, screen, fireEvent } from '@testing-library/vue';
import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
import { lessonResponsesStrings } from 'kolibri-common/strings/lessonResponsesStrings';
import LessonResourcePromptsModal from '../LessonResourcePromptsModal';

const { addQuestionAction$, questionNumberLabel$, removeQuestionAction$ } = lessonResponsesStrings;
const { saveAction$, cancelAction$ } = coreStrings;

const PROMPTS = [
  { id: 'prompt-1', text: 'Answer question 1 on page 2' },
  { id: 'prompt-2', text: 'Summarize section 3' },
];

function renderModal(prompts = PROMPTS) {
  return render(LessonResourcePromptsModal, {
    props: { resourceTitle: 'Photosynthesis reading', prompts },
  });
}

function questionBox(number) {
  return screen.getByRole('textbox', { name: questionNumberLabel$({ number }) });
}

describe('LessonResourcePromptsModal', () => {
  it('shows the existing questions', () => {
    renderModal();
    expect(questionBox(1)).toHaveValue('Answer question 1 on page 2');
    expect(questionBox(2)).toHaveValue('Summarize section 3');
  });

  it('starts with one empty question when there are none', () => {
    renderModal([]);
    expect(questionBox(1)).toHaveValue('');
  });

  it('saves edited, added and removed questions', async () => {
    const { emitted } = renderModal();
    await fireEvent.update(questionBox(1), 'Answer question 1 on page 3');
    await fireEvent.click(
      screen.getByRole('button', { name: removeQuestionAction$({ number: 2 }) }),
    );
    await fireEvent.click(screen.getByRole('button', { name: addQuestionAction$() }));
    await fireEvent.update(questionBox(2), '  What surprised you?  ');
    await fireEvent.click(screen.getByRole('button', { name: saveAction$() }));

    const [savedPrompts] = emitted().submit[0];
    expect(savedPrompts).toHaveLength(2);
    expect(savedPrompts[0]).toEqual({ id: 'prompt-1', text: 'Answer question 1 on page 3' });
    expect(savedPrompts[1].text).toBe('What surprised you?');
    expect(savedPrompts[1].id).toMatch(/^[0-9a-f]{32}$/);
  });

  it('leaves out empty questions', async () => {
    const { emitted } = renderModal();
    await fireEvent.update(questionBox(2), '   ');
    await fireEvent.click(screen.getByRole('button', { name: saveAction$() }));
    expect(emitted().submit[0][0]).toEqual([PROMPTS[0]]);
  });

  it('cancels without saving', async () => {
    const { emitted } = renderModal();
    await fireEvent.click(screen.getByRole('button', { name: cancelAction$() }));
    expect(emitted().cancel).toHaveLength(1);
    expect(emitted().submit).toBeUndefined();
  });
});
