"""Print the latest traces of a request type from Jaeger as an indented tree.

Reads Jaeger's API v3 (http://127.0.0.1:16686/api/v3), so every service's
spans in the trace show, TEI's included.

    .venv/bin/python tools/runtime/show_trace.py "answer request" [--count 1] [--minutes 60]
"""

import argparse
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime, timedelta

JAEGER = "http://127.0.0.1:16686/api/v3"


def get(path, **params):
    with urllib.request.urlopen(f"{JAEGER}/{path}?{urllib.parse.urlencode(params)}", timeout=30) as r:
        return json.load(r)


def spans_of(result):
    """(service, span) for every span in an OTLP JSON result."""
    for rs in result.get("resourceSpans", []):
        attrs = {a["key"]: a["value"].get("stringValue") for a in rs["resource"].get("attributes", [])}
        for ss in rs.get("scopeSpans", []):
            for span in ss.get("spans", []):
                yield attrs.get("service.name", "?"), span


def print_tree(trace_id):
    spans = list(spans_of(get(f"traces/{trace_id}")["result"]))
    children = defaultdict(list)
    ids = {s["spanId"] for _, s in spans}
    for service, s in spans:
        children[s.get("parentSpanId") if s.get("parentSpanId") in ids else None].append((service, s))

    def walk(parent, depth):
        for service, s in sorted(children[parent], key=lambda x: int(x[1]["startTimeUnixNano"])):
            ms = (int(s["endTimeUnixNano"]) - int(s["startTimeUnixNano"])) / 1e6
            print(f"{'  ' * depth}{s['name']}  [{service}, {ms:,.0f} ms]")
            walk(s["spanId"], depth + 1)

    walk(None, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("operation", help='the parent span\'s name, e.g. "answer request"')
    parser.add_argument("--service", default="lms-app")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--minutes", type=int, default=60)
    args = parser.parse_args()
    now = datetime.now(UTC)
    found = get("traces", **{
        "query.service_name": args.service, "query.operation_name": args.operation,
        "query.start_time_min": (now - timedelta(minutes=args.minutes)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query.start_time_max": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "query.num_traces": args.count,
    })["result"]
    trace_ids = list(dict.fromkeys(s["traceId"] for _, s in spans_of(found)))
    for trace_id in trace_ids[:args.count]:
        print(f"trace {trace_id}")
        print_tree(trace_id)
        print()
    if not trace_ids:
        print("No traces found.")


if __name__ == "__main__":
    main()
