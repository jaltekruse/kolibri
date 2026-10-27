/*
 * Kolibri's trackprogress API for a guest, kept in the page: a guest's progress
 * lasts only as long as their session with a resource, as Kolibri keeps none of it
 * beyond (kolibri/core/logger/viewsets/progress_tracking.py).
 */

const ATTEMPT_FIELDS = [
  'id',
  'correct',
  'complete',
  'hinted',
  'error',
  'item',
  'answer',
  'time_spent',
];

export class ProgressTrackingError extends Error {}

function newId() {
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
}

// ProgressTrackingViewSet._normalize_progress
function normalizeProgress(progress) {
  return Math.max(0, Math.min(1, Math.ceil(progress * 1000) / 1000));
}

// InteractionSerializer's defaults
function withDefaults(interaction) {
  return { complete: false, error: false, hinted: false, replace: false, ...interaction };
}

// ProgressTrackingViewSet._update_attempt
function updateAttempt(attempt, interaction) {
  attempt.time_spent = interaction.time_spent;
  if (interaction.error && !attempt.error) {
    attempt.error = true;
  }
  // Marked hinted only if not already correct, and never unmarked
  if (interaction.hinted && !attempt.hinted && !attempt.correct) {
    attempt.hinted = true;
  }
  if (interaction.replace) {
    attempt.correct = interaction.correct;
    if ('answer' in interaction) {
      attempt.answer = interaction.answer;
    }
  }
  if (interaction.complete && !attempt.complete) {
    attempt.complete = true;
  }
}

// ProgressTrackingViewSet._get_attemptlog, for a guest
function findAttempt(session, interaction) {
  if (interaction.id) {
    const attempt = session.attempts.find(a => a.id === interaction.id);
    if (!attempt) {
      throw new ProgressTrackingError('Invalid attemptlog id specified');
    }
    return attempt;
  }
  if (interaction.replace) {
    return session.attempts.find(a => a.item === interaction.item);
  }
  return undefined;
}

// ProgressTrackingViewSet._update_or_create_attempts: consecutive interactions with
// the same item are one attempt
function updateOrCreateAttempts(session, interactions) {
  const groups = [];
  for (const interaction of interactions.map(withDefaults)) {
    const last = groups[groups.length - 1];
    if (last && last[0].item === interaction.item) {
      last.push(interaction);
    } else {
      groups.push([interaction]);
    }
  }
  return groups.map(group => {
    let attempt = findAttempt(session, group[0]);
    let updates = group;
    if (!attempt) {
      const { item, correct, complete, hinted, error, answer = {}, time_spent } = group[0];
      attempt = { id: newId(), item, correct, complete, hinted, error, answer, time_spent };
      session.attempts.push(attempt);
      updates = group.slice(1);
    }
    updates.forEach(interaction => updateAttempt(attempt, interaction));
    return Object.fromEntries(ATTEMPT_FIELDS.map(field => [field, attempt[field]]));
  });
}

export default function createProgressTracking() {
  const sessions = new Map();

  return {
    /**
     * Starts a session with a resource, as a POST to trackprogress/ does.
     * @param {object} data - The POST's data: node_id, and mastery_model for an
     * assessment
     * @returns {object} The response's data
     * @throws {ProgressTrackingError} When data starts anything but a resource
     */
    start(data) {
      if (!data.node_id) {
        throw new ProgressTrackingError('A guest can only start a session with a resource');
      }
      const session = { progress: 0, time_spent: 0, attempts: [] };
      const id = newId();
      sessions.set(id, session);
      const output = { progress: 0, extra_fields: {}, time_spent: 0, complete: false };
      if (data.mastery_model) {
        Object.assign(output, {
          mastery_criterion: data.mastery_model,
          pastattempts: [],
          totalattempts: 0,
        });
      }
      return { ...output, session_id: id, context: { node_id: data.node_id } };
    },

    /**
     * Updates a session, as a PUT to trackprogress/<id>/ does.
     * @param {string} id - The session
     * @param {object} data - The PUT's data
     * @returns {object|null} The response's data, or null when there is no such session
     * @throws {ProgressTrackingError} When data is not a valid update
     */
    update(id, data) {
      const session = sessions.get(id);
      if (!session) {
        return null;
      }
      if ('progress_delta' in data && 'progress' in data) {
        throw new ProgressTrackingError(
          'must not pass progress_delta and progress in the same request',
        );
      }
      if ('progress_delta' in data) {
        session.progress = normalizeProgress(session.progress + data.progress_delta);
      } else if ('progress' in data) {
        session.progress = normalizeProgress(data.progress);
      }
      if ('time_spent_delta' in data) {
        session.time_spent += data.time_spent_delta;
      }
      const output = { complete: session.progress >= 1 };
      if (data.interactions) {
        output.attempts = updateOrCreateAttempts(session, data.interactions);
      }
      return output;
    },
  };
}
