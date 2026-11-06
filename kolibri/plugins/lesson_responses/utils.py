"""
Learners answer prompts on lesson items: coach-written questions on a lesson resource,
or the problems a coach listed for a web page in a lesson (see models.LessonWebPage).
Answers are stored in the existing logging models:

- one ContentSummaryLog and one MasteryLog per learner per lesson item, under a
  content_id derived from the lesson and item ids;
- one AttemptLog per answered prompt, with the prompt id (or problem number) as its
  item. Its answer holds the learner's work as a base64 encoded Free Math document,
  which is also where the coach's score, feedback and highlights go when they grade it.

Submitting completes the MasteryLog and its AttemptLogs, and sets progress to 1.
"""

import re
import uuid

_RESPONSE_CONTENT_ID_NAMESPACE = uuid.UUID("3b6f1e52-8d4a-4c1e-9a7b-2f5d0c8e6a14")

# Stored as the log kind, so these logs are never mistaken for a ContentNode kind.
RESPONSE_KIND = "lesson_response"

# Answers are collected in a single round, until resubmission is supported.
RESPONSE_MASTERY_LEVEL = 1

# Key of the Free Math document in AttemptLog.answer
ANSWER_KEY = "free_math"

# Base64 characters in one answer's document, so that saving one answer stays
# under Django's default DATA_UPLOAD_MAX_MEMORY_SIZE of 2.5 MB per request.
MAX_ANSWER_LENGTH = 2 * 1024 * 1024


# Problems a coach can list for one web page
MAX_PROBLEMS = 100

# "21-35", "21 to 35", optionally stepping: "21-35 by 3", "21-35 by 3s", "21-35/3"
_PROBLEM_RANGE = re.compile(
    r"^(\d+)\s*(?:-|\u2013|to)\s*(\d+)(?:\s*(?:by|/)\s*(\d+)\s*'?s?)?$",
    re.IGNORECASE,
)
_PROBLEM_SEPARATOR = re.compile(r",|;|\band\b", re.IGNORECASE)


def get_response_content_id(lesson_id, item_id):
    """
    The content_id the logs for the responses to one lesson item are stored under:
    a lesson resource's contentnode_id, or a lesson web page's id. It includes the
    lesson so the same resource in two lessons keeps separate answers.
    """
    key = f"{lesson_id}:{item_id}"
    return uuid.uuid5(_RESPONSE_CONTENT_ID_NAMESPACE, key).hex


def expand_problem_numbers(problem_numbers):
    """
    The problems a coach listed, in order, without repeats. For example
    "1-10, 21-35 by 3s" is 1 to 10, then 21, 24, 27, 30 and 33. Anything that is not
    a range, like "4a" or "Review 2", is kept as written.

    :param str problem_numbers: problem numbers and ranges, separated by commas,
        semicolons or "and"
    :rtype: list of str
    :raises ValueError: for a range that runs backwards, a step of 0, no problems,
        or more than MAX_PROBLEMS problems
    """
    problems = []
    for part in _PROBLEM_SEPARATOR.split(problem_numbers):
        part = " ".join(part.split())
        if not part:
            continue
        problem_range = _PROBLEM_RANGE.match(part)
        if problem_range is None:
            problems.append(part)
        else:
            start, end = int(problem_range[1]), int(problem_range[2])
            step = int(problem_range[3] or 1)
            if end < start or step < 1:
                raise ValueError(f"Invalid range of problems: {part}")
            if len(problems) + (end - start) // step + 1 > MAX_PROBLEMS:
                raise ValueError(f"More than {MAX_PROBLEMS} problems")
            problems.extend(str(number) for number in range(start, end + 1, step))
        if len(problems) > MAX_PROBLEMS:
            raise ValueError(f"More than {MAX_PROBLEMS} problems")
    problems = list(dict.fromkeys(problems))
    if not problems:
        raise ValueError("No problems listed")
    return problems
