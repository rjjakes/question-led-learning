"""Tracing: OpenTelemetry spans sent over OTLP to Jaeger (tech spec, Tracing).

The exporter reads OTEL_EXPORTER_OTLP_ENDPOINT and the resource reads
OTEL_SERVICE_NAME, both from the environment (Config.load puts .env there).
"""

import httpx2
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.langchain import LangchainInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

tracer = trace.get_tracer("lms")


def setup():
    """Send spans to the OTLP endpoint and turn on the packages that record LLM calls, SQL and HTTP."""
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    LangchainInstrumentor().instrument()
    PsycopgInstrumentor().instrument()
    return provider


def http_client(timeout):
    """An HTTP client for the OpenAI SDK that puts the current trace's traceparent header on every request,
    so TEI's and vLLM's own spans join the app's trace (OpenTelemetry, Context propagation).

    The SDK uses httpx2, which OpenTelemetry's httpx package doesn't patch, so this uses propagate.inject."""
    return httpx2.Client(timeout=timeout, event_hooks={"request": [lambda request: propagate.inject(request.headers)]})
