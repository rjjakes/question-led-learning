"""Extractor and Chunker."""

import pytest

from lms.ingest import MAX_TOKENS, Chunker, Extractor, load_tokenizer

ARTICLE = {
    "name": "Pressure ulcer",
    "url": "https://en.wikipedia.org/wiki/Pressure_ulcer",
    "sections": [
        {"type": "section", "name": "Abstract", "has_parts": [{"type": "paragraph", "value": "Lead text."}]},
        {"type": "section", "name": "Prevention", "has_parts": [
            {"type": "paragraph", "value": "Turn the patient."},
            {"type": "list", "has_parts": [{"type": "list_item", "value": "Every two hours"},
                                           {"type": "list_item", "value": "Check skin"}]},
            {"type": "section", "name": "Mattresses", "has_parts": [
                {"type": "table", "table_references": [{"identifier": "t1"}]},
                {"type": "image", "images": [{"caption": "A mattress"}]},
            ]},
        ]},
    ],
    "tables": [{"identifier": "t1", "headers": [[{"value": "Type"}, {"value": "Use"}]],
                "rows": [[{"value": "Foam"}, {"value": "Low risk"}]]}],
}


def test_extractor_headings_text_and_tables():
    md = Extractor().markdown(ARTICLE)
    assert md.startswith("# Pressure ulcer\n\nLead text.")
    assert "## Abstract" not in md
    assert "## Prevention\n\nTurn the patient." in md
    assert "- Every two hours\n- Check skin" in md
    assert "### Mattresses" in md
    assert "| Type | Use |\n| --- | --- |\n| Foam | Low risk |" in md
    assert "A mattress" not in md


@pytest.fixture(scope="module")
def chunker():
    return Chunker(load_tokenizer("Qwen/Qwen3-Embedding-0.6B"))


def test_chunks_carry_headings_and_stay_under_the_limit(chunker):
    long_section = {"type": "section", "name": "Management",
                    "has_parts": [{"type": "paragraph", "value": f"Sentence number {i} about care. " * 20}
                                  for i in range(30)]}
    chunks = chunker.split(Extractor().markdown(ARTICLE | {"sections": ARTICLE["sections"] + [long_section]}))
    assert all(chunker.tokens(c) <= MAX_TOKENS for c in chunks)
    management = [c for c in chunks if "## Management" in c]
    assert len(management) > 1
    assert all(c.startswith("# Pressure ulcer\n## Management\n") for c in management)
    assert any(c.startswith("# Pressure ulcer\n## Prevention\n### Mattresses\n") for c in chunks)
