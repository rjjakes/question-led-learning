"""Ingest: extract → chunk → embed → store the article and its chunks (tech spec, Flow 1).

Extractor turns an article's section tree from clientdocs.duckdb into Markdown,
Chunker splits it by heading and then by length, and Indexer embeds and stores
the chunks.
"""

import json
import logging

import duckdb
from huggingface_hub import hf_hub_download
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from tokenizers import Tokenizer

from lms.tracing import tracer

log = logging.getLogger(__name__)

# TEI cuts inputs over 512 tokens without an error (tech spec, Assumptions); the margin covers the end-of-text
# token TEI adds
MAX_TOKENS = 500
OVERLAP_TOKENS = 50
HEADINGS = [("#" * n, f"h{n}") for n in range(1, 7)]


class ClientDocsSource:
    """Reads articles from clientdocs.duckdb, the POC material."""

    def __init__(self, path):
        self.db = duckdb.connect(str(path), read_only=True)

    def article(self, title):
        """The row's name, url, sections and tables, or None."""
        row = self.db.execute("SELECT name, url, sections, tables FROM articles WHERE name = ?", [title]).fetchone()
        if row is None:
            return None
        name, url, sections, tables = row
        return {"name": name, "url": url, "sections": json.loads(sections or "[]"), "tables": json.loads(tables or "[]")}


class Extractor:
    """An article's section tree to Markdown, with its headings as heading lines.

    Sections become headings by depth under the title; paragraphs, list items and definitions become text;
    tables become Markdown tables. Images and galleries carry no text and are left out."""

    def markdown(self, article):
        tables = {t.get("identifier"): t for t in article["tables"]}
        lines = [f"# {article['name']}", ""]
        for part in article["sections"]:
            # The lead section is named "Abstract" in the dataset but has no heading on Wikipedia
            if part.get("type") == "section" and part.get("name") == "Abstract":
                self._parts(part.get("has_parts", []), tables, 1, lines)
            else:
                self._parts([part], tables, 1, lines)
        return "\n".join(lines).strip() + "\n"

    def _parts(self, parts, tables, depth, lines, indent=0):
        for part in parts:
            kind = part.get("type")
            value = (part.get("value") or "").strip()
            children = part.get("has_parts", [])
            if kind == "section":
                lines += [f"{'#' * min(depth + 1, 6)} {part.get('name', '')}", ""]
                self._parts(children, tables, depth + 1, lines)
            elif kind == "list":
                self._parts(children, tables, depth, lines, indent)
                if indent == 0:
                    lines.append("")
            elif kind == "list_item":
                if value:
                    lines.append(f"{'  ' * indent}- {value}")
                self._parts(children, tables, depth, lines, indent + 1)
            elif kind == "table":
                for ref in part.get("table_references", []):
                    table = tables.get(ref.get("identifier"))
                    if table:
                        lines += [*self._table(table), ""]
            elif kind in ("image", "gallery"):
                continue
            else:  # paragraph, definition_list, definition and any other part with text
                if value:
                    lines += [value, ""]
                self._parts(children, tables, depth, lines, indent)

    @staticmethod
    def _table(table):
        def row(cells):
            return "| " + " | ".join(str(c.get("value", "")).replace("|", "\\|").replace("\n", " ") for c in cells) + " |"

        headers, rows = table.get("headers") or [], table.get("rows") or []
        if not headers and rows:
            headers, rows = rows[:1], rows[1:]
        if not headers:
            return []
        width = max(len(r) for r in headers + rows)
        out = [row(h) for h in headers[:1]]
        out.append("|" + " --- |" * width)
        out += [row(r) for r in headers[1:] + rows]
        return out


def load_tokenizer(model):
    """The embedding model's own tokenizer, from the Hugging Face cache if it is there."""
    try:
        path = hf_hub_download(model, "tokenizer.json", local_files_only=True)
    except Exception:
        path = hf_hub_download(model, "tokenizer.json")
    return Tokenizer.from_file(path)


class Chunker:
    """Splits Markdown by heading, then to under MAX_TOKENS tokens with overlap.

    Each chunk starts with its heading path, so a chunk keeps the article and section it came from."""

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.by_heading = MarkdownHeaderTextSplitter(headers_to_split_on=HEADINGS, strip_headers=True)

    def tokens(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False).ids)

    def split(self, markdown):
        chunks = []
        for section in self.by_heading.split_text(markdown):
            prefix = "".join(f"{'#' * int(key[1])} {value}\n" for key, value in section.metadata.items())
            by_length = RecursiveCharacterTextSplitter(
                chunk_size=MAX_TOKENS - self.tokens(prefix), chunk_overlap=OVERLAP_TOKENS, length_function=self.tokens)
            for piece in by_length.split_text(section.page_content):
                chunk = prefix + piece
                if self.tokens(chunk) > MAX_TOKENS:
                    raise ValueError(f"chunk of {self.tokens(chunk)} tokens is over {MAX_TOKENS}: {chunk[:80]!r}")
                chunks.append(chunk)
        return chunks


class Indexer:
    """Embeds chunks and stores them with their article."""

    def __init__(self, embeddings, store):
        self.embeddings = embeddings
        self.store = store

    def index(self, title, source, chunks):
        vectors = self.embeddings.embed_documents(chunks)
        return self.store.save_article(title, source, list(zip(chunks, vectors)))


def ingest(titles, source, extractor, chunker, indexer, store):
    """Ingests each title not yet stored, one trace per article. Returns (ingested, skipped, missing) titles."""
    stored = store.article_ids(titles)
    ingested, missing = [], []
    for title in titles:
        if title in stored:
            continue
        with tracer.start_as_current_span("ingest request", attributes={"lms.article": title}) as span:
            article = source.article(title)
            if article is None:
                missing.append(title)
                span.set_attribute("lms.missing", True)
                continue
            with tracer.start_as_current_span("extract"):
                markdown = extractor.markdown(article)
            chunks = chunker.split(markdown)
            span.set_attribute("lms.chunks", len(chunks))
            indexer.index(article["name"], article["url"], chunks)
            ingested.append(title)
            log.info("ingested %s: %d chunks", title, len(chunks))
    return ingested, list(stored), missing
