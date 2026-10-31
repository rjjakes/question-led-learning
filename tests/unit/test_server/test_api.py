"""The JSON learner loop (lms/server/api.py), over an in-memory store with stand-ins for the LLM steps."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lms.server import api
from lms.server.learning import MAX_RESTATEMENTS, AnswerFlow, AttemptLog, Score


class FakeStore:
    """Course 1 has two checked questions; course 2 has none."""

    def __init__(self):
        self._questions = [{"id": n, "course_id": 1, "position": n, "scenario": f"S{n}", "question": f"Q{n}",
                            "answer": f"A{n}", "status": "checked"} for n in (1, 2)]
        self._learners = []
        self._attempts = []

    def courses(self):
        return [{"id": 1, "title": "Course", "questions": 2}, {"id": 2, "title": "Empty", "questions": 0}]

    def course(self, course_id):
        return {1: {"id": 1, "topic_id": 1, "title": "Course"}, 2: {"id": 2, "topic_id": 1, "title": "Empty"}}.get(course_id)

    def questions(self, course_id, status=None):
        return [q for q in self._questions if q["course_id"] == course_id and status in (None, q["status"])]

    def question(self, question_id):
        return next(q for q in self._questions if q["id"] == question_id)

    def create_learner(self):
        self._learners.append(len(self._learners) + 1)
        return self._learners[-1]

    def learner_exists(self, learner_id):
        return learner_id in self._learners

    def attempts(self, learner_id, course_id):
        return [a for a in self._attempts if a["learner_id"] == learner_id]

    def save_attempt(self, learner_id, question_id, restatement, shown_text, answer, score):
        self._attempts.append({"learner_id": learner_id, "question_id": question_id, "restatement": restatement,
                               "shown_text": shown_text, "answer": answer, "score": score})


class FakeScorer:
    """Passes the answer "right" and fails any other; "error" stands for a failed LLM call."""

    def score(self, shown_text, model_answer, answer):
        if answer == "error":
            raise RuntimeError("LLM call failed")
        return Score(passed=answer == "right", feedback="Feedback.")


class FakeRestater:
    def restate(self, question, last_shown, last_answer, n):
        return f"Restatement {n} of {question['question']}"


def client():
    store = FakeStore()
    attempt_log = AttemptLog(store)
    app = FastAPI()
    app.state.learning = api.Learning(store, attempt_log, AnswerFlow(store, FakeScorer(), FakeRestater(), attempt_log))
    app.include_router(api.router)
    return TestClient(app)


def start(c):
    learner_id = c.post("/api/courses/1/start").json()["learner_id"]
    return f"/api/learn/{learner_id}/1"


def send(c, url, place, answer):
    q = place["question"]
    return c.post(url, json={"question_id": q["id"], "restatement": q["restatement"], "shown_text": q["text"],
                             "answer": answer})


def test_courses():
    assert client().get("/api/courses").json() == [{"id": 1, "title": "Course", "questions": 2}]


def test_learner_loop():
    c = client()
    url = start(c)
    place = c.get(url).json()
    assert place == {"course_id": 1, "course_title": "Course", "number": 1, "total": 2,
                     "max_restatements": MAX_RESTATEMENTS, "question": {"id": 1, "restatement": 0, "text": "S1\n\nQ1"}}

    for n in range(1, MAX_RESTATEMENTS + 1):
        assert send(c, url, place, "wrong").json() == {"passed": False, "feedback": "Feedback.", "step": "restate",
                                                       "restated": f"Restatement {n} of Q1", "model_answer": None}
        place = c.get(url).json()
        assert place["question"] == {"id": 1, "restatement": n, "text": f"Restatement {n} of Q1"}
    outcome = send(c, url, place, "wrong").json()
    assert (outcome["step"], outcome["model_answer"]) == ("reveal", "A1")

    place = c.get(url).json()
    assert (place["number"], place["question"]["id"]) == (2, 2)
    assert send(c, url, place, "right").json()["step"] == "next"
    place = c.get(url).json()
    assert (place["number"], place["question"]) == (None, None)
    assert c.get(f"{url}/results").json() == [
        {"number": 1, "question": "Q1", "passed": False, "restatements": MAX_RESTATEMENTS},
        {"number": 2, "question": "Q2", "passed": True, "restatements": 0}]


def test_answer_not_to_current_place():
    c = client()
    url = start(c)
    place = c.get(url).json()
    assert send(c, url, place, "right").status_code == 200
    assert send(c, url, place, "right").status_code == 409


def test_failed_scoring_records_nothing():
    c = client()
    url = start(c)
    place = c.get(url).json()
    assert send(c, url, place, "error").status_code == 503
    assert c.get(url).json() == place


def test_unknown_course_or_learner():
    c = client()
    assert c.post("/api/courses/9/start").status_code == 404
    assert c.get("/api/learn/9/1").status_code == 404
    assert c.get("/api/learn/9/1/results").status_code == 404
