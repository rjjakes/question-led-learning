"""ProgressRule and AttemptLog.place."""

from lms.learning import MAX_RESTATEMENTS, AttemptLog, progress_rule


def test_progress_rule():
    assert progress_rule(True, 0) == "next"
    assert progress_rule(False, 0) == "restate"
    assert progress_rule(False, MAX_RESTATEMENTS - 1) == "restate"
    assert progress_rule(False, MAX_RESTATEMENTS) == "reveal"


class FakeStore:
    def __init__(self, attempts):
        self._attempts = attempts

    def questions(self, course_id, status=None):
        return [{"id": 1, "position": 1}, {"id": 2, "position": 2}]

    def attempts(self, learner_id, course_id):
        return self._attempts


def attempt(question_id, restatement, score):
    return {"question_id": question_id, "restatement": restatement, "score": score,
            "shown_text": f"shown {restatement}", "answer": "a"}


def test_place():
    def place(attempts):
        p = AttemptLog(FakeStore(attempts)).place(1, 1)
        return (p.question["id"] if p.question else None), p.restatement

    assert place([]) == (1, 0)
    assert place([attempt(1, 0, False)]) == (1, 1)
    assert place([attempt(1, 0, False), attempt(1, 1, True)]) == (2, 0)
    assert place([attempt(1, r, False) for r in range(MAX_RESTATEMENTS + 1)]) == (2, 0)
    assert place([attempt(1, 0, True), attempt(2, 0, True)]) == (None, 0)
