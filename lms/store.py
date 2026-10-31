"""Store: every database read and write, as own SQL through psycopg 3 (tech spec, Classes).

Vectors go through pgvector-python (register_vector). AttemptLog's writes are
here too, as save_attempt.
"""

from dataclasses import dataclass

import numpy as np
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


@dataclass(frozen=True)
class Chunk:
    id: int
    article_id: int
    article_title: str
    text: str


class Store:
    def __init__(self, config):
        self.pool = ConnectionPool(config.database_url, min_size=1, max_size=4, open=True,
                                   configure=register_vector, kwargs={"row_factory": dict_row})

    def close(self):
        self.pool.close()

    # Articles and chunks (filled by ingest)

    def article_ids(self, titles):
        """{title: id} for the titles already stored."""
        with self.pool.connection() as conn:
            rows = conn.execute("SELECT id, title FROM articles WHERE title = ANY(%s)", [list(titles)]).fetchall()
        return {r["title"]: r["id"] for r in rows}

    def save_article(self, title, source, chunks):
        """Stores an article and its (text, embedding) chunks in one transaction; returns its id."""
        with self.pool.connection() as conn, conn.transaction():
            article_id = conn.execute("INSERT INTO articles (title, source) VALUES (%s, %s) RETURNING id",
                                      [title, source]).fetchone()["id"]
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO chunks (article_id, text, embedding) VALUES (%s, %s, %s)",
                                [(article_id, text, np.asarray(embedding, dtype=np.float32))
                                 for text, embedding in chunks])
        return article_id

    def search_chunks(self, article_ids, embedding, k):
        """The k chunks of the given articles nearest to the embedding, by cosine distance."""
        with self.pool.connection() as conn, conn.transaction():
            # Without an iterative scan, HNSW filters its first ef_search hits and can return fewer than k
            # (pgvector README, Iterative Index Scans)
            conn.execute("SET LOCAL hnsw.iterative_scan = strict_order")
            rows = conn.execute(
                """SELECT c.id, c.article_id, a.title, c.text FROM chunks c JOIN articles a ON a.id = c.article_id
                   WHERE c.article_id = ANY(%s) ORDER BY c.embedding <=> %s LIMIT %s""",
                [list(article_ids), np.asarray(embedding, dtype=np.float32), k]).fetchall()
        return [Chunk(r["id"], r["article_id"], r["title"], r["text"]) for r in rows]

    # Topics and courses (filled by a user)

    def create_topic(self, title, article_ids):
        with self.pool.connection() as conn, conn.transaction():
            topic_id = conn.execute("INSERT INTO topics (title) VALUES (%s) RETURNING id", [title]).fetchone()["id"]
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO topic_articles (topic_id, article_id) VALUES (%s, %s)",
                                [(topic_id, a) for a in article_ids])
        return topic_id

    def topic_article_ids(self, topic_id, titles):
        """{title: id} for those of the titles that are in the topic."""
        with self.pool.connection() as conn:
            rows = conn.execute(
                """SELECT a.id, a.title FROM articles a JOIN topic_articles t ON t.article_id = a.id
                   WHERE t.topic_id = %s AND a.title = ANY(%s)""", [topic_id, list(titles)]).fetchall()
        return {r["title"]: r["id"] for r in rows}

    def create_course(self, topic_id, title, article_ids):
        with self.pool.connection() as conn, conn.transaction():
            course_id = conn.execute("INSERT INTO courses (topic_id, title) VALUES (%s, %s) RETURNING id",
                                     [topic_id, title]).fetchone()["id"]
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO course_articles (course_id, article_id) VALUES (%s, %s)",
                                [(course_id, a) for a in article_ids])
        return course_id

    def courses(self):
        with self.pool.connection() as conn:
            return conn.execute(
                """SELECT c.id, c.title, count(q.id) FILTER (WHERE q.status = 'checked') AS questions
                   FROM courses c LEFT JOIN questions q ON q.course_id = c.id GROUP BY c.id ORDER BY c.id""").fetchall()

    def course(self, course_id):
        with self.pool.connection() as conn:
            return conn.execute("SELECT id, topic_id, title FROM courses WHERE id = %s", [course_id]).fetchone()

    def course_articles(self, course_id):
        """{title: id} of the course's articles."""
        with self.pool.connection() as conn:
            rows = conn.execute(
                """SELECT a.id, a.title FROM articles a JOIN course_articles c ON c.article_id = a.id
                   WHERE c.course_id = %s ORDER BY a.title""", [course_id]).fetchall()
        return {r["title"]: r["id"] for r in rows}

    # Questions

    def save_questions(self, course_id, questions):
        """Appends questions to the course in the given order. Each is a dict with scenario, question,
        answer, status and article_ids."""
        with self.pool.connection() as conn, conn.transaction():
            # Locks the course row so two saves can't take the same positions
            conn.execute("SELECT id FROM courses WHERE id = %s FOR UPDATE", [course_id])
            position = conn.execute("SELECT coalesce(max(position), 0) AS p FROM questions WHERE course_id = %s",
                                    [course_id]).fetchone()["p"]
            ids = []
            for q in questions:
                position += 1
                question_id = conn.execute(
                    """INSERT INTO questions (course_id, position, scenario, question, answer, status)
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                    [course_id, position, q["scenario"], q["question"], q["answer"], q["status"]]).fetchone()["id"]
                with conn.cursor() as cur:
                    cur.executemany("INSERT INTO question_articles (question_id, article_id) VALUES (%s, %s)",
                                    [(question_id, a) for a in q["article_ids"]])
                ids.append(question_id)
        return ids

    def update_question(self, question_id, **fields):
        """Sets the given columns (scenario, question, answer, status): a user's correction."""
        allowed = {k: v for k, v in fields.items() if k in ("scenario", "question", "answer", "status") and v is not None}
        if allowed:
            with self.pool.connection() as conn:
                conn.execute(f"UPDATE questions SET {', '.join(f'{k} = %s' for k in allowed)} WHERE id = %s",
                             [*allowed.values(), question_id])

    def questions(self, course_id, status=None):
        """The course's questions in course order, each with its article titles."""
        with self.pool.connection() as conn:
            return conn.execute(
                """SELECT q.id, q.position, q.scenario, q.question, q.answer, q.status,
                          array_agg(a.title ORDER BY a.title) AS articles
                   FROM questions q JOIN question_articles qa ON qa.question_id = q.id JOIN articles a ON a.id = qa.article_id
                   WHERE q.course_id = %s AND (%s::text IS NULL OR q.status = %s)
                   GROUP BY q.id ORDER BY q.position""", [course_id, status, status]).fetchall()

    def question(self, question_id):
        """A question with its answer (the Answer flow's load)."""
        with self.pool.connection() as conn:
            return conn.execute(
                "SELECT id, course_id, position, scenario, question, answer, status FROM questions WHERE id = %s",
                [question_id]).fetchone()

    # Learners and attempts

    def create_learner(self):
        with self.pool.connection() as conn:
            return conn.execute("INSERT INTO learners DEFAULT VALUES RETURNING id").fetchone()["id"]

    def learner_exists(self, learner_id):
        with self.pool.connection() as conn:
            return conn.execute("SELECT 1 FROM learners WHERE id = %s", [learner_id]).fetchone() is not None

    def attempts(self, learner_id, course_id):
        """The learner's attempts at the course's questions, oldest first."""
        with self.pool.connection() as conn:
            return conn.execute(
                """SELECT t.question_id, t.restatement, t.shown_text, t.answer, t.score, t.answered_at
                   FROM attempts t JOIN questions q ON q.id = t.question_id
                   WHERE t.learner_id = %s AND q.course_id = %s ORDER BY t.id""", [learner_id, course_id]).fetchall()

    def save_attempt(self, learner_id, question_id, restatement, shown_text, answer, score):
        """AttemptLog: records an answer, its score and the restatement it answered."""
        with self.pool.connection() as conn:
            conn.execute(
                """INSERT INTO attempts (learner_id, question_id, restatement, shown_text, answer, score, answered_at)
                   VALUES (%s, %s, %s, %s, %s, %s, now())""",
                [learner_id, question_id, restatement, shown_text, answer, score])
