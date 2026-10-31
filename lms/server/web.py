"""The learner's screen: a scenario and an open question, answered in the learner's words (product spec, The design).
The same loop as JSON is under /v1 (lms/server/api.py).

    .venv/bin/python -m lms.server.web     then open http://127.0.0.1:8001
"""

import html
import logging

import uvicorn
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from lms.server import api
from lms.server.learning import AnswerFlow, AnswerScorer, AttemptLog, MAX_RESTATEMENTS, QuestionRestater
from lms.utils import tracing
from lms.utils.clients import LLMClient
from lms.utils.config import Config
from lms.utils.store import Store

PORT = 8001
log = logging.getLogger(__name__)

config = Config.load()
tracing.setup()
store = Store(config)
llm = LLMClient(config)
attempt_log = AttemptLog(store)
flow = AnswerFlow(store, AnswerScorer(llm), QuestionRestater(llm), attempt_log)
app = FastAPI(title="Question-led learning")
app.state.learning = api.Learning(store, attempt_log, flow)
app.include_router(api.router)

STYLE = """
:root { --fg: #1a1a1a; --muted: #5a5a5a; --line: #d6d6d6; --pass: #1d6b3a; --fail: #8a4b00; --bg: #fff; --panel: #f6f6f4; }
body { font: 17px/1.55 system-ui, sans-serif; max-width: 44rem; margin: 2rem auto; padding: 0 1rem; color: var(--fg); background: var(--bg); }
h1 { font-size: 1.3rem; margin: 0 0 0.2rem; }
.meta { color: var(--muted); font-size: 0.9rem; margin: 0 0 1.5rem; }
.question { white-space: pre-wrap; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 1rem 1.2rem; }
textarea { width: 100%; box-sizing: border-box; min-height: 9rem; font: inherit; padding: 0.6rem; margin: 1rem 0 0.6rem; }
button, .button { font: inherit; padding: 0.45rem 1.1rem; border: 1px solid var(--fg); border-radius: 4px; background: var(--fg); color: var(--bg); text-decoration: none; cursor: pointer; }
.feedback { border-left: 4px solid; padding: 0.4rem 0.9rem; margin: 0 0 1.4rem; }
.feedback.pass { border-color: var(--pass); } .feedback.fail { border-color: var(--fail); }
.feedback strong.pass { color: var(--pass); } .feedback strong.fail { color: var(--fail); }
.answer { white-space: pre-wrap; border: 1px dashed var(--line); padding: 0.8rem 1rem; margin-bottom: 1.4rem; }
ul.courses { padding: 0; list-style: none; } ul.courses li { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: 0.6rem 0; border-bottom: 1px solid var(--line); }
"""


def page(title, body, meta=""):
    return HTMLResponse(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title><style>{STYLE}</style></head><body>
<h1>{html.escape(title)}</h1><p class="meta">{meta}</p>
{body}
</body></html>""")


def esc(text):
    return html.escape(text or "")


def course_or_404(course_id):
    course = store.course(course_id)
    if course is None:
        raise HTTPException(404, "No such course")
    return course


def learner_or_404(learner_id):
    if not store.learner_exists(learner_id):
        raise HTTPException(404, "No such learner")


def question_form(learner_id, course_id, question_id, restatement, shown_text):
    label = "Your answer" if restatement == 0 else f"Try again (restatement {restatement} of {MAX_RESTATEMENTS})"
    return f"""<div class="question">{esc(shown_text)}</div>
<form method="post" action="/learn/{learner_id}/{course_id}">
<input type="hidden" name="question_id" value="{question_id}">
<input type="hidden" name="restatement" value="{restatement}">
<input type="hidden" name="shown_text" value="{esc(shown_text)}">
<label for="answer" class="meta">{label}</label>
<textarea id="answer" name="answer" required></textarea>
<button>Submit answer</button>
</form>"""


def plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def progress_meta(course, place):
    ids = [q["id"] for q in store.questions(course["id"], status="checked")]
    if place.question is None:
        return plural(len(ids), "question")
    return f"Question {ids.index(place.question['id']) + 1} of {len(ids)}"


@app.get("/", response_class=HTMLResponse)
def index():
    rows = "".join(
        f'<li><span>{esc(c["title"])} <span class="meta">· {plural(c["questions"], "question")}</span></span>'
        f'<form method="post" action="/courses/{c["id"]}/start"><button>Start</button></form></li>'
        for c in store.courses() if c["questions"])
    return page("Courses", f'<ul class="courses">{rows}</ul>' if rows else "<p>No courses with questions yet.</p>")


@app.post("/courses/{course_id}/start")
def start(course_id: int):
    course_or_404(course_id)
    return RedirectResponse(f"/learn/{store.create_learner()}/{course_id}", status_code=303)


@app.get("/learn/{learner_id}/{course_id}", response_class=HTMLResponse)
def show(learner_id: int, course_id: int):
    """Shows the learner's current question, or the end of the course."""
    learner_or_404(learner_id)
    course = course_or_404(course_id)
    place = attempt_log.place(learner_id, course_id)
    if place.question is None:
        return page("Course complete", '<p>You have answered every question.</p><a class="button" href="/">Courses</a>',
                    progress_meta(course, place))
    form = question_form(learner_id, course_id, place.question["id"], place.restatement, flow.shown_text(place))
    return page(course["title"], form, progress_meta(course, place))


@app.post("/learn/{learner_id}/{course_id}", response_class=HTMLResponse)
def answer(learner_id: int, course_id: int, question_id: int = Form(), restatement: int = Form(),
           shown_text: str = Form(), answer: str = Form()):
    learner_or_404(learner_id)
    course = course_or_404(course_id)
    place = attempt_log.place(learner_id, course_id)
    # A form that is no longer the learner's place (sent twice, or from an old tab) goes back to the current question
    if place.question is None or place.question["id"] != question_id or place.restatement != restatement:
        return RedirectResponse(f"/learn/{learner_id}/{course_id}", status_code=303)
    try:
        outcome = flow.answer(learner_id, question_id, restatement, shown_text, answer)
    except Exception:
        # The LLM call failed twice (lms.utils.clients.ATTEMPTS); nothing was recorded, so the learner can send it again
        log.exception("answer request failed")
        body = ('<div class="feedback fail"><strong class="fail">Your answer couldn\'t be scored just now.</strong> '
                'Please send it again.</div>' + question_form(learner_id, course_id, question_id, restatement, shown_text))
        return page(course["title"], body, progress_meta(course, place))
    verdict = '<strong class="pass">Good answer.</strong>' if outcome.passed else '<strong class="fail">Not quite.</strong>'
    body = f'<div class="feedback {"pass" if outcome.passed else "fail"}">{verdict} {esc(outcome.feedback)}</div>'
    next_link = f'<a class="button" href="/learn/{learner_id}/{course_id}">Next question</a>'
    if outcome.step == "restate":
        body += question_form(learner_id, course_id, question_id, restatement + 1, outcome.restated)
    elif outcome.step == "reveal":
        body += f'<p class="meta">The answer</p><div class="answer">{esc(outcome.model_answer)}</div>{next_link}'
    else:
        body += next_link
    return page(course["title"], body, progress_meta(course, place))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
