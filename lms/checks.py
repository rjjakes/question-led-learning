"""Code checks on LLM replies. Each returns the reply's problems as sentences, empty if there are none;
LLMClient.text sends a reply with problems back to the LLM with them."""

import re

# The Markdown the prompts rule out
MARKDOWN = {
    "headings": re.compile(r"^#{1,6} ", re.M),
    "bold text": re.compile(r"\*\*|__"),
    "list lines": re.compile(r"^\s*([-*+]|\d+[.)]) ", re.M),
}
# The AnswerDrafter prompt's limit
MAX_ANSWER_WORDS = 150
# Ways a reply refers to the source passages it was given; "the sources of ..." is left alone
SOURCES = re.compile(r"\bsources? \d+\b|\bsource passages?\b|\b(the|these|provided) sources\b(?! of)", re.I)
YOU = re.compile(r"\byou(r|rs|rself)?\b", re.I)
# Guess, not tested: a run of this many words copied from the model answer gives the point away
# rather than hinting at it
COPIED_WORDS = 8


def markdown(text):
    found = [name for name, pattern in MARKDOWN.items() if pattern.search(text)]
    return [f"It uses Markdown ({', '.join(found)}); write plain prose."] if found else []


def answer_problems(text):
    """AnswerDrafter's rules: plain prose, at most MAX_ANSWER_WORDS words, no mention of the sources."""
    problems = markdown(text)
    count = len(text.split())
    if count > MAX_ANSWER_WORDS:
        problems.append(f"It has {count} words; the limit is {MAX_ANSWER_WORDS}.")
    if SOURCES.search(text):
        problems.append("It mentions the sources; state the points without them.")
    return problems


def words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def copied_run(text, model_answer, n=COPIED_WORDS):
    """The first run of n words in text that is also in model_answer, or None."""
    answer = words(model_answer)
    runs = {tuple(answer[i:i + n]) for i in range(len(answer) - n + 1)}
    shown = words(text)
    for i in range(len(shown) - n + 1):
        if tuple(shown[i:i + n]) in runs:
            return " ".join(shown[i:i + n])
    return None


def restatement_problems(text, model_answer):
    """QuestionRestater's rules: plain text, one question, addressed to the learner, the answer not copied."""
    problems = markdown(text)
    marks = text.count("?")
    if marks != 1:
        problems.append(f"It has {marks} question marks; ask one question.")
    if not YOU.search(text):
        problems.append('It isn\'t addressed to the learner as "you".')
    run = copied_run(text, model_answer)
    if run:
        problems.append(f'It copies "{run}" from the model answer; hint at the point instead.')
    return problems
