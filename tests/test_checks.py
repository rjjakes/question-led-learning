"""The reply checks: answer_problems and restatement_problems."""

from lms.checks import MAX_ANSWER_WORDS, answer_problems, restatement_problems


def test_answer_checks_pass_plain_prose():
    assert answer_problems("Check where the link really goes before you click it, and report the message.") == []
    assert answer_problems("word " * MAX_ANSWER_WORDS) == []
    assert answer_problems("The sources of the risk are links and attachments.") == []


def test_answer_checks_find_markdown_length_and_sources():
    assert answer_problems("## Answer\n\nCheck the link.") == ["It uses Markdown (headings); write plain prose."]
    assert answer_problems("**Check** the link.") == ["It uses Markdown (bold text); write plain prose."]
    assert answer_problems("Key points:\n- Check the link\n1. Report it") == [
        "It uses Markdown (list lines); write plain prose."]
    assert answer_problems("word " * (MAX_ANSWER_WORDS + 1)) == [
        f"It has {MAX_ANSWER_WORDS + 1} words; the limit is {MAX_ANSWER_WORDS}."]
    sources = ["It mentions the sources; state the points without them."]
    assert answer_problems("As Source 2 says, check the link.") == sources
    assert answer_problems("The sources say to check the link.") == sources


MODEL_ANSWER = "Hover over the link to see where it really goes, and report the message to your IT team."


def test_restatement_checks_pass_one_question_to_you():
    text = ("You get the same email again, and the link text shows the bank's name. "
            "Where could you look to see where the link leads?")
    assert restatement_problems(text, MODEL_ANSWER) == []


def test_restatement_checks_find_markdown_questions_you_and_copying():
    assert restatement_problems("**Scenario:** You get the email again. What do you do?", MODEL_ANSWER) == [
        "It uses Markdown (bold text); write plain prose."]
    assert restatement_problems("You get the email again. What do you check? Who do you tell?", MODEL_ANSWER) == [
        "It has 2 question marks; ask one question."]
    assert restatement_problems("The email arrives again. What should be done?", MODEL_ANSWER) == [
        'It isn\'t addressed to the learner as "you".']
    copied = "You could hover over the link to see where it really goes. What else should you do?"
    assert restatement_problems(copied, MODEL_ANSWER) == [
        'It copies "hover over the link to see where it" from the model answer; hint at the point instead.']
