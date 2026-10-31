"""The learner loop as JSON, for the React frontend (tech spec, Frontend). The routes mirror the HTML pages in
lms.server.web, under /api, the prefix NVIDIA's RAG Blueprint frontend puts on its backend calls
(frontend/vite.config.ts). Pydantic models give what they take and return, as in its rag_server/server.py.

lms.server.web builds the store and the learner loop and puts them on app.state (Starlette, Applications)."""

import logging
from dataclasses import asdict, dataclass
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from lms.server.learning import MAX_RESTATEMENTS, AnswerFlow, AttemptLog
from lms.utils.store import Store

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@dataclass(frozen=True)
class Learning:
    store: Store
    attempt_log: AttemptLog
    flow: AnswerFlow


def get_learning(request: Request):
    return request.app.state.learning


LearningDep = Annotated[Learning, Depends(get_learning)]


class CourseItem(BaseModel):
    id: int
    title: str
    questions: int  # checked questions


class StartResponse(BaseModel):
    learner_id: int


class QuestionShown(BaseModel):
    id: int
    restatement: int  # 0 for the original question
    text: str         # the scenario and question, or the restatement the learner answers


class PlaceResponse(BaseModel):
    """Where the learner is in the course. question is None once every question is answered."""
    course_id: int
    course_title: str
    number: int | None  # the question's place in the course, from 1
    total: int
    max_restatements: int
    question: QuestionShown | None


class AnswerRequest(BaseModel):
    question_id: int
    restatement: int
    shown_text: str
    answer: str


class OutcomeResponse(BaseModel):
    passed: bool
    feedback: str
    step: Literal["next", "restate", "reveal"]
    restated: str | None      # the restated question, after "restate"
    model_answer: str | None  # the question's answer, after "reveal"


def course_or_404(store, course_id):
    course = store.course(course_id)
    if course is None:
        raise HTTPException(404, "No such course")
    return course


def learner_or_404(store, learner_id):
    if not store.learner_exists(learner_id):
        raise HTTPException(404, "No such learner")


@router.get("/courses", response_model=list[CourseItem])
def courses(learning: LearningDep):
    """The courses with checked questions."""
    return [c for c in learning.store.courses() if c["questions"]]


@router.post("/courses/{course_id}/start", response_model=StartResponse)
def start(course_id: int, learning: LearningDep):
    course_or_404(learning.store, course_id)
    return {"learner_id": learning.store.create_learner()}


@router.get("/learn/{learner_id}/{course_id}", response_model=PlaceResponse)
def show(learner_id: int, course_id: int, learning: LearningDep):
    """The learner's current question, or none at the end of the course."""
    learner_or_404(learning.store, learner_id)
    course = course_or_404(learning.store, course_id)
    place = learning.attempt_log.place(learner_id, course_id)
    ids = [q["id"] for q in learning.store.questions(course_id, status="checked")]
    question = None
    if place.question is not None:
        question = {"id": place.question["id"], "restatement": place.restatement,
                    "text": learning.flow.shown_text(place)}
    return {"course_id": course["id"], "course_title": course["title"],
            "number": ids.index(place.question["id"]) + 1 if place.question else None, "total": len(ids),
            "max_restatements": MAX_RESTATEMENTS, "question": question}


@router.post("/learn/{learner_id}/{course_id}", response_model=OutcomeResponse, responses={
    409: {"description": "The answer isn't to the learner's current question or restatement"},
    503: {"description": "The answer couldn't be scored; nothing was recorded, so it can be sent again"}})
def answer(learner_id: int, course_id: int, body: AnswerRequest, learning: LearningDep):
    learner_or_404(learning.store, learner_id)
    course_or_404(learning.store, course_id)
    place = learning.attempt_log.place(learner_id, course_id)
    # An answer that is no longer to the learner's place (sent twice, or from an old tab)
    if place.question is None or place.question["id"] != body.question_id or place.restatement != body.restatement:
        raise HTTPException(409, "Not the learner's current question")
    try:
        outcome = learning.flow.answer(learner_id, body.question_id, body.restatement, body.shown_text, body.answer)
    except Exception:
        # The LLM call failed twice (lms.utils.clients.ATTEMPTS)
        log.exception("answer request failed")
        raise HTTPException(503, "The answer couldn't be scored; send it again")
    return asdict(outcome)
