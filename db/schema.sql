-- The tech spec's data model (docs/tech-spec.md, Data model).
-- Ids are bigint identity and text columns are text; each join table's
-- primary key is its two ids. Apply once to an empty database:
--   docker exec -i lms-postgres psql -U lms -d lms -v ON_ERROR_STOP=1 < db/schema.sql

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE topics (
    id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title text NOT NULL
);

CREATE TABLE articles (
    id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title  text NOT NULL,
    source text NOT NULL
);

CREATE TABLE topic_articles (
    topic_id   bigint NOT NULL REFERENCES topics,
    article_id bigint NOT NULL REFERENCES articles,
    PRIMARY KEY (topic_id, article_id)
);

CREATE TABLE courses (
    id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    topic_id bigint NOT NULL REFERENCES topics,
    title    text NOT NULL
);

CREATE TABLE course_articles (
    course_id  bigint NOT NULL REFERENCES courses,
    article_id bigint NOT NULL REFERENCES articles,
    PRIMARY KEY (course_id, article_id)
);

CREATE TABLE chunks (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    article_id bigint NOT NULL REFERENCES articles,
    text       text NOT NULL,
    embedding  vector(1024) NOT NULL
);

-- The Retriever orders by cosine distance (<=>)
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE questions (
    id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    course_id bigint NOT NULL REFERENCES courses,
    position  integer NOT NULL,
    scenario  text NOT NULL,
    question  text NOT NULL,
    answer    text NOT NULL,
    status    text NOT NULL,  -- draft, checked or rejected
    UNIQUE (course_id, position)
);

CREATE TABLE question_articles (
    question_id bigint NOT NULL REFERENCES questions,
    article_id  bigint NOT NULL REFERENCES articles,
    PRIMARY KEY (question_id, article_id)
);

CREATE TABLE learners (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY
);

CREATE TABLE attempts (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    learner_id  bigint NOT NULL REFERENCES learners,
    question_id bigint NOT NULL REFERENCES questions,
    restatement integer NOT NULL,  -- 0 for the original question
    shown_text  text NOT NULL,
    answer      text NOT NULL,
    score       boolean NOT NULL,  -- pass or fail
    answered_at timestamptz NOT NULL
);
