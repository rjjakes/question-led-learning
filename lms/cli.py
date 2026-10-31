"""Command line for ingest and course setup (product spec, Course setup).

    .venv/bin/python -m lms.cli ingest data/test-articles.txt
    .venv/bin/python -m lms.cli create-topic "Sample topic" data/test-articles.txt
    .venv/bin/python -m lms.cli create-course TOPIC_ID "Course title" "Article title" ...
    .venv/bin/python -m lms.cli generate COURSE_ID "make 3 questions about wound care" --count 3
    .venv/bin/python -m lms.cli add-question COURSE_ID --scenario ... --question ... --article "Article title"
    .venv/bin/python -m lms.cli edit-question QUESTION_ID [--scenario ...] [--question ...] [--answer ...] [--status ...]
    .venv/bin/python -m lms.cli questions COURSE_ID
"""

import argparse
import logging
import sys
from pathlib import Path

from lms import tracing
from lms.clients import EmbeddingClient, LLMClient
from lms.config import Config
from lms.store import Store


def read_titles(path):
    return [line.strip() for line in Path(path).read_text().splitlines() if line.strip()]


def cmd_ingest(args, config, store):
    from lms.ingest import Chunker, Extractor, Indexer, ClientDocsSource, ingest, load_tokenizer
    ingested, skipped, missing = ingest(
        read_titles(args.titles_file), ClientDocsSource(config.clientdocs_db), Extractor(),
        Chunker(load_tokenizer(config.embed_model)), Indexer(EmbeddingClient(config), store), store)
    print(f"{len(ingested)} ingested, {len(skipped)} already stored, {len(missing)} not in {config.clientdocs_db.name}")
    for title in missing:
        print(f"  missing: {title}")


def cmd_create_topic(args, config, store):
    titles = read_titles(args.titles_file)
    ids = store.article_ids(titles)
    unknown = [t for t in titles if t not in ids]
    if unknown:
        sys.exit(f"Not ingested yet: {', '.join(unknown)}")
    print(f"topic {store.create_topic(args.title, ids.values())}: {args.title}, {len(ids)} articles")


def cmd_create_course(args, config, store):
    ids = store.topic_article_ids(args.topic_id, args.articles)
    unknown = [t for t in args.articles if t not in ids]
    if unknown:
        sys.exit(f"Not in topic {args.topic_id}: {', '.join(unknown)}")
    print(f"course {store.create_course(args.topic_id, args.title, ids.values())}: {args.title}, {len(ids)} articles")


def course_setup(config, store):
    from lms.course import AnswerDrafter, CourseSetup, QuestionChecker, QuestionGenerator, Retriever
    llm = LLMClient(config)
    return CourseSetup(store, Retriever(EmbeddingClient(config), store), QuestionGenerator(llm),
                       QuestionChecker(llm), AnswerDrafter(llm))


def print_questions(questions):
    for q in questions:
        print(f"[{q['id']}] #{q['position']} {q['status']} ({'; '.join(q['articles'])})")
        print(f"  Scenario: {q['scenario']}\n  Question: {q['question']}\n  Answer: {q['answer']}\n")


def cmd_generate(args, config, store):
    ids = course_setup(config, store).generate(args.course_id, args.request, args.count)
    print_questions([q for q in store.questions(args.course_id) if q["id"] in ids])


def cmd_add_question(args, config, store):
    ids = course_setup(config, store).add(args.course_id, args.scenario, args.question, args.article)
    print_questions([q for q in store.questions(args.course_id) if q["id"] in ids])


def cmd_edit_question(args, config, store):
    store.update_question(args.question_id, scenario=args.scenario, question=args.question, answer=args.answer,
                          status=args.status)
    print(f"question {args.question_id} updated")


def cmd_questions(args, config, store):
    print_questions(store.questions(args.course_id))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="lms.cli", description="Ingest and course setup")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("ingest", help="extract, chunk, embed and store articles from clientdocs.duckdb")
    p.add_argument("titles_file", help="one article title per line")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("create-topic", help="group ingested articles into a topic")
    p.add_argument("title")
    p.add_argument("titles_file")
    p.set_defaults(func=cmd_create_topic)

    p = sub.add_parser("create-course", help="a course drawing on articles of a topic")
    p.add_argument("topic_id", type=int)
    p.add_argument("title")
    p.add_argument("articles", nargs="+", help="article titles")
    p.set_defaults(func=cmd_create_course)

    p = sub.add_parser("generate", help="draft questions from the course's articles, check them and draft answers")
    p.add_argument("course_id", type=int)
    p.add_argument("request", help="what the questions should be about; also the search text")
    p.add_argument("--count", type=int, default=3)
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("add-question", help="a question written by the user; it is checked and its answer drafted")
    p.add_argument("course_id", type=int)
    p.add_argument("--scenario", required=True)
    p.add_argument("--question", required=True)
    p.add_argument("--article", action="append", required=True, help="an article the question draws on")
    p.set_defaults(func=cmd_add_question)

    p = sub.add_parser("edit-question", help="correct a question, its scenario or its answer")
    p.add_argument("question_id", type=int)
    p.add_argument("--scenario")
    p.add_argument("--question")
    p.add_argument("--answer")
    p.add_argument("--status", choices=["draft", "checked", "rejected"], help="only checked questions reach learners")
    p.set_defaults(func=cmd_edit_question)

    p = sub.add_parser("questions", help="list a course's questions")
    p.add_argument("course_id", type=int)
    p.set_defaults(func=cmd_questions)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    config = Config.load()
    provider = tracing.setup()
    store = Store(config)
    try:
        args.func(args, config, store)
    finally:
        store.close()
        provider.shutdown()


if __name__ == "__main__":
    main()
