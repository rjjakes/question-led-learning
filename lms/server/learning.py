"""The learner loop: ask, answer, score, then move on or restate (product spec, The learner loop; tech spec, Flow 3).

One Answer request is one trace: load the question and its answer, score the
learner's answer, apply the ProgressRule, restate after a fail, save the attempt.
"""

import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field

from lms.utils.checks import restatement_problems
from lms.utils.tracing import tracer

log = logging.getLogger(__name__)

# Restatements before the answer is shown and the learner moves on (default agreed for the build;
# product spec, Open: Repeated low scores)
MAX_RESTATEMENTS = 2


class Score(BaseModel):
    passed: bool = Field(description="True if the learner's answer gets the key points of the model answer right")
    feedback: str = Field(description="One or two sentences to the learner: what was right and what is missing, "
                                      "without giving the answer away")


class AnswerScorer:
    """Scores a learner's free-text answer against the question's answer: pass or fail."""

    PROMPT = """You mark a learner's answer to a course question against the model answer. Pass it if it gets \
the key points of the model answer right, in any wording; small omissions are fine. Fail it if it is wrong, \
misses the main point or doesn't answer the question.

Then write feedback to the learner, addressed as "you", in one or two sentences: what they got right, and \
what kind of point is missing. Never state the missing points or any part of the model answer; if they \
failed, they will get hints next."""

    def __init__(self, llm):
        self.llm = llm

    def score(self, shown_text, model_answer, answer):
        return self.llm.json("AnswerScorer", Score, [
            ("system", self.PROMPT),
            ("user", f"Question as shown to the learner:\n{shown_text}\n\nModel answer:\n{model_answer}\n\n"
                     f"Learner's answer:\n{answer}"),
        ])


class QuestionRestater:
    """After a fail, restates the question with more context and partial details of its answer."""

    PROMPT = """A learner's answer to a course question was marked as not good enough. Restate the question \
so they can try again: keep the situation, add more context, and bake partial details of the model answer into \
the question as hints, without giving the whole answer. This is restatement {n} of {max}: give more help than \
the text they last saw. Reply with the restated scenario and question only, addressed to the learner."""

    def __init__(self, llm):
        self.llm = llm

    def restate(self, question, last_shown, last_answer, n):
        return self.llm.text("QuestionRestater", [
            ("system", self.PROMPT.format(n=n, max=MAX_RESTATEMENTS)),
            ("user", f"Original scenario: {question['scenario']}\nOriginal question: {question['question']}\n\n"
                     f"Model answer:\n{question['answer']}\n\nText the learner last saw:\n{last_shown}\n\n"
                     f"Learner's answer:\n{last_answer}"),
        ], check=lambda text: restatement_problems(text, question["answer"]))


def progress_rule(passed, restatement):
    """ProgressRule: "next" after a pass, "restate" after a fail while restatements are left, else "reveal"
    (show the answer, then move on)."""
    if passed:
        return "next"
    return "restate" if restatement < MAX_RESTATEMENTS else "reveal"


def original_text(question):
    return f"{question['scenario']}\n\n{question['question']}"


def final_attempt(attempts):
    """The attempt that finished a question: a pass, or the answer to its last restatement. None if unfinished."""
    return next((a for a in attempts if a["score"] or a["restatement"] >= MAX_RESTATEMENTS), None)


@dataclass(frozen=True)
class Place:
    """Where a learner is in a course: the current question and which restatement of it they answer next."""
    question: dict | None
    restatement: int
    last_shown: str | None = None
    last_answer: str | None = None


@dataclass(frozen=True)
class Result:
    """How a finished question went: passed, or shown the answer after the last restatement."""
    number: int        # the question's place in the course, from 1
    question: dict
    passed: bool
    restatements: int  # restatements answered before the learner passed or was shown the answer


class AttemptLog:
    """Records each answer, its score and the restatement it answered, and reads back where a learner is."""

    def __init__(self, store):
        self.store = store

    def record(self, learner_id, question_id, restatement, shown_text, answer, passed):
        self.store.save_attempt(learner_id, question_id, restatement, shown_text, answer, passed)

    def results(self, learner_id, course_id):
        """How each question the learner has finished went, in course order."""
        attempts = self.store.attempts(learner_id, course_id)
        results = []
        for number, question in enumerate(self.store.questions(course_id, status="checked"), 1):
            final = final_attempt([a for a in attempts if a["question_id"] == question["id"]])
            if final:
                results.append(Result(number, question, final["score"], final["restatement"]))
        return results

    def place(self, learner_id, course_id):
        """The first checked question the learner hasn't passed or run out of restatements on."""
        attempts = self.store.attempts(learner_id, course_id)
        for question in self.store.questions(course_id, status="checked"):
            mine = [a for a in attempts if a["question_id"] == question["id"]]
            if final_attempt(mine):
                continue
            if not mine:
                return Place(question, 0)
            last = mine[-1]
            return Place(question, last["restatement"] + 1, last["shown_text"], last["answer"])
        return Place(None, 0)


@dataclass(frozen=True)
class Outcome:
    passed: bool
    feedback: str
    step: str                  # "next", "restate" or "reveal"
    restated: str | None       # the restated question, after "restate"
    model_answer: str | None   # the question's answer, after "reveal"


class AnswerFlow:
    def __init__(self, store, scorer, restater, attempt_log):
        self.store = store
        self.scorer = scorer
        self.restater = restater
        self.attempt_log = attempt_log

    def answer(self, learner_id, question_id, restatement, shown_text, answer):
        with tracer.start_as_current_span("answer request", attributes={
                "lms.learner": learner_id, "lms.question": question_id, "lms.restatement": restatement}):
            question = self.store.question(question_id)
            score = self.scorer.score(shown_text, question["answer"], answer)
            step = progress_rule(score.passed, restatement)
            restated = None
            if step == "restate":
                restated = self._restate(question, shown_text, answer, restatement + 1)
            self.attempt_log.record(learner_id, question_id, restatement, shown_text, answer, score.passed)
            return Outcome(score.passed, score.feedback, step, restated, question["answer"] if step == "reveal" else None)

    def shown_text(self, place):
        """The text to show for the learner's place. A restatement made in an earlier request isn't stored
        (attempts hold only what was answered), so it is made again here."""
        if place.restatement == 0:
            return original_text(place.question)
        with tracer.start_as_current_span("restate request", attributes={"lms.question": place.question["id"]}):
            return self._restate(place.question, place.last_shown, place.last_answer, place.restatement)

    def _restate(self, question, last_shown, last_answer, n):
        """Restatement n, or the last text again if the restater's call or its checks fail."""
        try:
            return self.restater.restate(question, last_shown, last_answer, n)
        except Exception:
            log.exception("QuestionRestater failed; showing the last text again")
            return last_shown
