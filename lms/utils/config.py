"""Config: the settings for the current environment, from .env (tech spec, Configuration)."""

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_env_file(path):
    """KEY=value lines; blank lines and # comments are skipped."""
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


@dataclass(frozen=True)
class Config:
    llm_base_url: str
    llm_model: str
    embed_base_url: str
    embed_model: str
    database_url: str
    clientdocs_db: Path
    llm_api_key: str = field(repr=False)

    @classmethod
    def load(cls, path=ROOT / ".env"):
        """Settings from the process environment, falling back to the .env file.

        OTEL_* settings are left in the environment, where the OpenTelemetry SDK reads them."""
        for key, value in read_env_file(path).items():
            os.environ.setdefault(key, value)
        clientdocs_db = Path(os.environ["CLIENTDOCS_DB"])
        return cls(
            llm_base_url=os.environ["LLM_BASE_URL"],
            llm_model=os.environ["LLM_MODEL"],
            embed_base_url=os.environ["EMBED_BASE_URL"],
            embed_model=os.environ["EMBED_MODEL"],
            database_url=os.environ["DATABASE_URL"],
            clientdocs_db=clientdocs_db if clientdocs_db.is_absolute() else ROOT / clientdocs_db,
            # Ollama needs no key; the OpenAI SDK needs a value all the same
            llm_api_key=os.environ.get("LLM_API_KEY", "unused"),
        )
