"""LLMClient and EmbeddingClient: the app's only ways to reach the two model services (tech spec, Classes)."""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from lms.tracing import http_client, tracer

# Qwen3-Embedding's query prompt (config_sentence_transformers.json, "prompts"); documents get none
QUERY_PROMPT = "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:"
# TEI's default --max-client-batch-size
EMBED_BATCH = 32
# A failed call or a reply that doesn't fit the schema is tried once more, then raised
ATTEMPTS = 2


class LLMClient:
    """Calls the OpenAI-compatible chat API; returns text or JSON."""

    def __init__(self, config):
        # "low" keeps some reasoning without letting it fill the 8,192-token context (tech spec, Open)
        self.chat = ChatOpenAI(base_url=config.llm_base_url, model=config.llm_model, api_key="unused",
                               reasoning_effort="low", http_client=http_client(timeout=600))

    def text(self, step, messages):
        """The reply as text. step names the call's span (run_name)."""
        reply = self.chat.with_retry(stop_after_attempt=ATTEMPTS).invoke(messages, config={"run_name": step})
        return reply.content.strip()

    def json(self, step, schema, messages):
        """The reply as an instance of the Pydantic model schema, through response_format json_schema."""
        runnable = self.chat.with_structured_output(schema).with_retry(stop_after_attempt=ATTEMPTS)
        return runnable.invoke(messages, config={"run_name": step})


class EmbeddingClient:
    """Calls the embedding service. OpenAIEmbeddings sends no LangChain callbacks, so each call gets its own span."""

    def __init__(self, config):
        self.model = OpenAIEmbeddings(base_url=config.embed_base_url + "/v1", model=config.embed_model,
                                      api_key="unused", check_embedding_ctx_length=False, chunk_size=EMBED_BATCH,
                                      http_client=http_client(timeout=120))

    def embed_documents(self, texts):
        with tracer.start_as_current_span("embed chunks", attributes={"lms.texts": len(texts)}):
            return self.model.embed_documents(texts)

    def embed_query(self, text):
        with tracer.start_as_current_span("embed search text"):
            return self.model.embed_query(QUERY_PROMPT + text)
