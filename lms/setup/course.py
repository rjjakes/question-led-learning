"""Course setup: draft or take questions, check them, draft their answers, store them (tech spec, Flow 2).

One Generate request is one trace: embed the search text, run one similarity
search over the course's articles, then the LLM steps, then save.
"""

import logging
from typing import Literal

from pydantic import BaseModel, Field

from lms.utils.checks import answer_problems
from lms.utils.tracing import tracer

log = logging.getLogger(__name__)

# Chunks per LLM call: 6 chunks of up to 500 tokens leave room in Ollama's 8,192-token context for the
# instructions, the model's reasoning and the reply (tech spec, Open: Context length)
K = 6


class Retriever:
    """Similarity search over the chunks of given articles."""

    def __init__(self, embeddings, store):
        self.embeddings = embeddings
        self.store = store

    def search(self, text, article_ids, k=K):
        return self.store.search_chunks(article_ids, self.embeddings.embed_query(text), k)


def sources(chunks):
    return "\n\n".join(f"[Source {i}] Article: {c.article_title}\n{c.text}" for i, c in enumerate(chunks, 1))


class DraftQuestion(BaseModel):
    scenario: str = Field(description='One to three sentences putting the learner, as "you", in a realistic situation')
    question: str = Field(description="One open question about what the learner would do or explain in the situation")
    articles: list[str] = Field(description="Titles, exactly as given, of the source articles the question draws on")


class DraftQuestions(BaseModel):
    questions: list[DraftQuestion]


class Check(BaseModel):
    verdict: Literal["keep", "rewrite", "reject"]
    scenario: str = Field(description="The scenario: unchanged for keep and reject, fixed for rewrite")
    question: str = Field(description="The question: unchanged for keep and reject, fixed for rewrite")
    reason: str = Field(description="One sentence on why")


class QuestionGenerator:
    """Drafts open questions as JSON from the course's articles: a scenario, the question and its articles."""

    PROMPT = """You write questions for a self-paced course. Learners answer each question in their own words, \
and their answers are marked against the source passages below.

Write {count} questions. For each:
- scenario: one to three sentences that put the learner, as "you", in a realistic situation they might face, \
such as "You receive an email that appears to come from your bank...". Only where the point can't be put as \
a situation, set out the context plainly instead.
- question: one open question about what the learner would do, notice or explain in that situation, and why, \
such as "What should you do next, and why?" or "Which signs in this message suggest it isn't genuine?". \
Not a yes/no question, not multiple choice, and not several questions in one.
- articles: the titles, exactly as given, of the source articles the question draws on.

Every question must be answerable from the sources alone, and each must cover a different point."""

    def __init__(self, llm):
        self.llm = llm

    def draft(self, request, chunks, count):
        reply = self.llm.json("QuestionGenerator", DraftQuestions, [
            ("system", self.PROMPT.format(count=count)),
            ("user", f"Request: {request}\n\nSources:\n\n{sources(chunks)}"),
        ])
        return reply.questions[:count]


class QuestionChecker:
    """Checks a question against its articles; keeps, rewrites or rejects it."""

    PROMPT = """You review one draft question for a self-paced course against its source passages. \
A good question:
- can be answered fully from the sources;
- is open: the learner must explain, describe or reason, not answer yes/no or give a single word;
- asks one thing, clearly;
- has a realistic scenario that agrees with the sources and doesn't give the answer away;
- puts the learner in the situation as "you", where the point allows.

Verdict "keep" if it meets all of these, "rewrite" if small changes fix it (give the fixed scenario and \
question), "reject" if the sources can't support it."""

    def __init__(self, llm):
        self.llm = llm

    def check(self, scenario, question, chunks):
        return self.llm.json("QuestionChecker", Check, [
            ("system", self.PROMPT),
            ("user", f"Scenario: {scenario}\nQuestion: {question}\n\nSources:\n\n{sources(chunks)}"),
        ])


class AnswerDrafter:
    """Drafts a question's answer from its articles; the user can correct it."""

    PROMPT = """Write the model answer to a course question, using only the source passages. Learners' \
answers will be marked against it, so state the key points a good answer must contain, in plain prose, in \
150 words or fewer. Don't mention the sources."""

    def __init__(self, llm):
        self.llm = llm

    def draft(self, scenario, question, chunks):
        return self.llm.text("AnswerDrafter", [
            ("system", self.PROMPT),
            ("user", f"Scenario: {scenario}\nQuestion: {question}\n\nSources:\n\n{sources(chunks)}"),
        ], check=answer_problems)


class CourseSetup:
    """The Generate flow, for drafted and user-written questions alike."""

    def __init__(self, store, retriever, generator, checker, drafter):
        self.store = store
        self.retriever = retriever
        self.generator = generator
        self.checker = checker
        self.drafter = drafter

    def generate(self, course_id, request, count):
        """Drafts count questions about the request; returns the stored questions' ids."""
        with tracer.start_as_current_span("generate request", attributes={"lms.course": course_id}):
            articles = self.store.course_articles(course_id)
            chunks = self.retriever.search(request, articles.values())
            drafts = self.generator.draft(request, chunks, count)
            questions = []
            for d in drafts:
                ids = [articles[t] for t in d.articles if t in articles] or sorted({c.article_id for c in chunks})
                questions.append(self._prepare(d.scenario, d.question, ids, chunks))
            return self.store.save_questions(course_id, questions)

    def add(self, course_id, scenario, question, titles):
        """A question written by the user, drawing on the given course articles."""
        with tracer.start_as_current_span("generate request", attributes={"lms.course": course_id}):
            articles = self.store.course_articles(course_id)
            unknown = [t for t in titles if t not in articles]
            if unknown:
                raise ValueError(f"Not in course {course_id}: {', '.join(unknown)}")
            ids = [articles[t] for t in titles]
            chunks = self.retriever.search(question, ids)
            return self.store.save_questions(course_id, [self._prepare(scenario, question, ids, chunks)])

    def _prepare(self, scenario, question, article_ids, chunks):
        """Checks the question against its own articles' chunks and drafts its answer. A step whose reply
        fails twice leaves the question as a draft for the user to finish."""
        own = [c for c in chunks if c.article_id in article_ids] or chunks
        q = {"scenario": scenario, "question": question, "answer": "", "status": "draft", "article_ids": article_ids}
        try:
            check = self.checker.check(scenario, question, own)
        except Exception:
            log.exception("QuestionChecker failed; left as a draft: %s", question)
            return q
        if check.verdict == "reject":
            log.info("rejected (%s): %s", check.reason, question)
            return q | {"status": "rejected"}
        q |= {"scenario": check.scenario, "question": check.question}
        try:
            q |= {"answer": self.drafter.draft(q["scenario"], q["question"], own), "status": "checked"}
        except Exception:
            log.exception("AnswerDrafter failed; left as a draft: %s", question)
        return q
