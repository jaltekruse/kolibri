import createProgressTracking, { ProgressTrackingError } from '../progressTracking';

const NODE_ID = 'a'.repeat(32);
const answer = value => ({ userInput: { 'numeric-input 1': { currentValue: value } } });

function startSession() {
  const progressTracking = createProgressTracking();
  const { session_id } = progressTracking.start({
    node_id: NODE_ID,
    mastery_model: { type: 'm_of_n', m: 2, n: 2 },
  });
  return { progressTracking, session_id };
}

describe('progressTracking', () => {
  it('adds up progress, rounding up, until the resource is complete', () => {
    const { progressTracking, session_id } = startSession();

    expect(progressTracking.update(session_id, { progress_delta: 0.3334 })).toEqual({
      complete: false,
    });
    expect(progressTracking.update(session_id, { progress_delta: 0.666 })).toEqual({
      complete: true,
    });
  });

  it('updates an attempt by its id, keeping the first answer unless replaced', () => {
    const { progressTracking, session_id } = startSession();
    const [first] = progressTracking.update(session_id, {
      interactions: [{ item: 'q1', correct: 0, time_spent: 3, answer: answer('1') }],
    }).attempts;

    const [hinted] = progressTracking.update(session_id, {
      interactions: [
        { id: first.id, item: 'q1', correct: 0, hinted: true, time_spent: 5, answer: {} },
      ],
    }).attempts;
    expect(hinted).toMatchObject({
      id: first.id,
      hinted: true,
      answer: answer('1'),
      time_spent: 5,
    });

    const [replaced] = progressTracking.update(session_id, {
      interactions: [
        {
          id: first.id,
          item: 'q1',
          correct: 1,
          complete: true,
          replace: true,
          time_spent: 8,
          answer: answer('2'),
        },
      ],
    }).attempts;
    expect(replaced).toMatchObject({
      id: first.id,
      correct: 1,
      complete: true,
      answer: answer('2'),
    });
  });

  it('makes one attempt of consecutive interactions with an item', () => {
    const { progressTracking, session_id } = startSession();

    const { attempts } = progressTracking.update(session_id, {
      interactions: [
        { item: 'q1', correct: 0, time_spent: 2, answer: answer('1') },
        { item: 'q1', correct: 0, error: true, time_spent: 4 },
        { item: 'q2', correct: 1, complete: true, time_spent: 6, answer: answer('3') },
      ],
    });

    expect(attempts.map(({ item, error, time_spent }) => ({ item, error, time_spent }))).toEqual([
      { item: 'q1', error: true, time_spent: 4 },
      { item: 'q2', error: false, time_spent: 6 },
    ]);
  });

  it('refuses an attempt id it has not given', () => {
    const { progressTracking, session_id } = startSession();

    expect(() =>
      progressTracking.update(session_id, {
        interactions: [{ id: 'b'.repeat(32), item: 'q1', correct: 1, time_spent: 1, answer: {} }],
      }),
    ).toThrow(ProgressTrackingError);
  });

  it('has no session it did not start', () => {
    expect(createProgressTracking().update('c'.repeat(32), { progress: 1 })).toBeNull();
  });
});
