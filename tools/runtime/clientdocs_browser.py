"""Browser for data/clientdocs.duckdb, the POC material.

Reads only that file. Lists its articles 100 to a page in title order,
and searches their titles with SQL. Each title opens the article's section
tree, tables and infoboxes; its "JSON" link shows the row itself.

Run from the project root:  .venv/bin/python tools/runtime/clientdocs_browser.py
Then open http://127.0.0.1:8000
"""

import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlencode

import duckdb
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

ROOT = Path(__file__).resolve().parent.parent.parent
DB = ROOT / "data/clientdocs.duckdb"
JSON_COLUMNS = ("sections", "infoboxes", "tables")
PER_PAGE = 100
PORT = 8000

if not DB.exists():
    sys.exit(f"No {DB}")
db = duckdb.connect(str(DB), read_only=True)
names = [name for (name,) in db.execute("SELECT name FROM articles ORDER BY name COLLATE NOCASE, name").fetchall()]
app = FastAPI(title="Client docs browser")

STYLE = """
body { font: 15px/1.5 system-ui, sans-serif; max-width: 60rem; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; background: #fff; overflow-wrap: break-word; }
h1 { font-size: 1.4rem; margin-bottom: 0.2rem; }
.meta { color: #555; margin-top: 0; }
form.search { display: flex; gap: 0.4rem; margin: 1rem 0; }
form.search input { flex: 1; min-width: 0; padding: 0.35rem 0.5rem; font: inherit; }
form.search button { padding: 0.35rem 0.8rem; font: inherit; }
nav { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; margin: 1rem 0; }
nav a, nav span { padding: 0.2rem 0.5rem; border: 1px solid #ccc; border-radius: 4px; text-decoration: none; }
nav span.off { color: #aaa; }
nav input { width: 5rem; }
ol { padding-left: 4.5rem; }
li { padding: 0.1rem 0; }
.part { color: #777; font-size: 0.9em; }
.scroll { overflow-x: auto; }
table.tbl { border-collapse: collapse; font-size: 0.9em; margin: 0.5rem 0 1rem; }
table.tbl th, table.tbl td { border: 1px solid #ccc; padding: 0.2rem 0.4rem; vertical-align: top; text-align: left; }
details { margin: 0.5rem 0; }
pre { white-space: pre-wrap; word-break: break-word; font-size: 0.85em; background: #f6f6f6; padding: 0.5rem; }
"""


def page_html(heading, body):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(heading)} · Client docs browser</title><style>{STYLE}</style></head><body>
<h1>{html.escape(heading)}</h1>
{body}
</body></html>"""


def url_of(name, route="article"):
    """A Wikipedia-style address: spaces become underscores, which titles never contain."""
    return f"/{route}/" + quote(name.replace(" ", "_"), safe="/")


def like(word):
    """An ILIKE pattern matching the word anywhere, with its own % and _ taken literally."""
    return "%" + re.sub(r"([\\%_])", r"\\\1", word) + "%"


def page_count(total):
    return max(1, -(-total // PER_PAGE))


def search(q, page):
    """(total, page, names) for the articles whose title contains every word of q.

    The page is moved back to the last one if it is past it."""
    words = q.split()
    where = " AND ".join("name ILIKE ? ESCAPE '\\'" for _ in words)
    params = [like(w) for w in words]
    with db.cursor() as cur:
        total = cur.execute(f"SELECT count(*) FROM articles WHERE {where}", params).fetchone()[0]
        page = min(page, page_count(total))
        # Exact title first, then titles holding the whole query, then the rest, each by title
        rows = cur.execute(f"""
            SELECT name FROM articles WHERE {where}
            ORDER BY lower(name) = lower(?) DESC, name ILIKE ? ESCAPE '\\' DESC, name COLLATE NOCASE
            LIMIT ? OFFSET ?
        """, params + [q, like(q), PER_PAGE, (page - 1) * PER_PAGE]).fetchall()
    return total, page, [name for (name,) in rows]


def pager(page, pages, params=None, base="/"):
    """Paging links that keep the page's other query parameters."""
    params = params or {}

    def link(n, label):
        if n < 1 or n > pages or n == page:
            return f'<span class="off">{label}</span>'
        return f'<a href="{base}?{html.escape(urlencode({**params, "page": n}))}">{label}</a>'

    hidden = "".join(f'<input type="hidden" name="{html.escape(k)}" value="{html.escape(str(v))}">'
                     for k, v in params.items())
    return (
        "<nav>"
        + link(1, "« First") + link(page - 1, "‹ Prev")
        + f'<form action="{base}">{hidden}Page <input type="number" name="page" min="1" max="{pages}" value="{page}"> of {pages:,}</form>'
        + link(page + 1, "Next ›") + link(pages, "Last »")
        + "</nav>"
    )


@app.get("/", response_class=HTMLResponse)
def index(page: int = Query(1, ge=1), q: str = ""):
    q = q.strip()
    if q:
        total, page, shown = search(q, page)
        start = (page - 1) * PER_PAGE
        meta = (f'{total:,} articles have every word of “{html.escape(q)}” in their title'
                ' · <a href="/">All articles</a>')
    else:
        total = len(names)
        page = min(page, page_count(total))
        start = (page - 1) * PER_PAGE
        shown = names[start:start + PER_PAGE]
        meta = f"Articles {start + 1:,}–{start + len(shown):,} of {total:,}, by title"
    pages = page_count(total)
    rows = "".join(f'<li><a href="{url_of(name)}">{html.escape(name)}</a></li>' for name in shown)
    return page_html("Client docs", f"""
<form class="search" action="/"><input type="search" name="q" value="{html.escape(q)}" placeholder="Search titles" aria-label="Search titles"><button>Search</button></form>
<p class="meta">{meta}</p>
{pager(page, pages, {"q": q} if q else {})}
{f'<ol start="{start + 1}">{rows}</ol>' if rows else "<p>No results.</p>"}
{pager(page, pages, {"q": q} if q else {})}""")


def article_row(path):
    """The article's row as a dict, with its JSON-encoded columns decoded."""
    with db.cursor() as cur:
        cur.execute("SELECT * FROM articles WHERE name = ?", [path.replace("_", " ")])
        values = cur.fetchone()
        if values is None:
            raise HTTPException(404, f"No article {path!r}")
        row = dict(zip([d[0] for d in cur.description], values))
    for column in JSON_COLUMNS:
        row[column] = json.loads(row[column]) if row[column] else []
    return row


def render_table(table):
    if not table:
        return '<p class="part">[table not found]</p>'

    def cells(row, tag):
        return "<tr>" + "".join(f"<{tag}>{html.escape(str(c.get('value', '')))}</{tag}>" for c in row) + "</tr>"

    head = "".join(cells(r, "th") for r in table.get("headers", []))
    body = "".join(cells(r, "td") for r in table.get("rows", []))
    return f'<div class="scroll"><table class="tbl"><thead>{head}</thead><tbody>{body}</tbody></table></div>'


def render_parts(parts, tables, depth=0):
    """HTML for a sections tree: sections become headings by depth, other parts by type."""
    out = []
    for part in parts:
        kind = part.get("type")
        children = part.get("has_parts", [])
        value = html.escape(part.get("value", ""))
        if kind == "section":
            level = min(depth + 2, 6)
            out.append(f"<h{level}>{html.escape(part.get('name', ''))}</h{level}>"
                       + render_parts(children, tables, depth + 1))
        elif kind == "paragraph":
            out.append(f"<p>{value}</p>")
        elif kind == "list":
            out.append(f"<ul>{render_parts(children, tables, depth)}</ul>")
        elif kind == "list_item":
            out.append(f"<li>{value}{render_parts(children, tables, depth)}</li>")
        elif kind == "definition_list":
            out.append(f"<dl>{render_parts(children, tables, depth)}</dl>")
        elif kind == "definition":
            out.append(f"<dd>{value}</dd>")
        elif kind == "table":
            out.extend(render_table(tables.get(ref.get("identifier"))) for ref in part.get("table_references", []))
        elif kind in ("image", "gallery"):
            captions = "; ".join(i.get("caption") or i.get("name", "") for i in part.get("images", []))
            out.append(f'<p class="part">[{kind}: {html.escape(captions)}]</p>')
        else:
            out.append(f'<p class="part">[{html.escape(str(kind))}] {value}</p>' + render_parts(children, tables, depth))
    return "".join(out)


@app.get("/article/{path:path}", response_class=HTMLResponse)
def article(path: str):
    row = article_row(path)
    tables = {t.get("identifier"): t for t in row["tables"]}
    infoboxes = "".join(
        f'<details><summary>Infobox: {html.escape(box.get("name", ""))}</summary>'
        f'<pre>{html.escape(json.dumps(box, ensure_ascii=False, indent=1))}</pre></details>'
        for box in row["infoboxes"]
    )
    links = (f'<a href="{html.escape(row["url"])}">Wikipedia</a>'
             f' · <a href="{url_of(row["name"], "json")}">JSON</a> · <a href="/">All articles</a>')
    version = row["version"] or {}
    return page_html(row["name"], f"""
<p class="meta">{html.escape(row.get("description") or "")}</p>
<p class="meta">{links} · revision {version.get("identifier")}, modified {row.get("date_modified")}</p>
{infoboxes}
{render_parts(row["sections"], tables)}""")


@app.get("/json/{path:path}")
def article_json(path: str):
    row = article_row(path)
    return Response(json.dumps(row, ensure_ascii=False, indent=1, default=str), media_type="application/json")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
