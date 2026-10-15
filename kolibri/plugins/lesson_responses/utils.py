"""
Learner answers to coach-written prompts are stored in the existing logging models,
so this plugin needs no tables of its own:

- one ContentSummaryLog and one MasteryLog per learner per lesson resource, under a
  content_id derived from the lesson and resource ids;
- one AttemptLog per answered prompt, with the prompt id as its item.

Submitting completes the MasteryLog and its AttemptLogs, and sets progress to 1.
"""

import uuid

_RESPONSE_CONTENT_ID_NAMESPACE = uuid.UUID("3b6f1e52-8d4a-4c1e-9a7b-2f5d0c8e6a14")

# Stored as the log kind, so these logs are never mistaken for a ContentNode kind.
RESPONSE_KIND = "lesson_response"

# Answers are collected in a single round, until resubmission is supported.
RESPONSE_MASTERY_LEVEL = 1

MAX_ANSWER_LENGTH = 10000

# AttemptLog.simple_answer is a CharField of this length.
SIMPLE_ANSWER_LENGTH = 200


def get_response_content_id(lesson_id, contentnode_id):
    """
    The content_id the logs for one lesson resource's responses are stored under.
    It includes the lesson so the same resource in two lessons keeps separate answers.
    """
    key = f"{lesson_id}:{contentnode_id}"
    return uuid.uuid5(_RESPONSE_CONTENT_ID_NAMESPACE, key).hex
