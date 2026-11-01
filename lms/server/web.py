"""The backend: the learner loop as JSON under /api (lms/server/api.py), which the React app in frontend/ calls.

    .venv/bin/python -m lms.server.web     serves http://127.0.0.1:8001/api
"""

import uvicorn
from fastapi import FastAPI

from lms.server import api
from lms.server.learning import AnswerFlow, AnswerScorer, AttemptLog, QuestionRestater
from lms.utils import tracing
from lms.utils.clients import LLMClient
from lms.utils.config import Config
from lms.utils.store import Store

PORT = 8001

config = Config.load()
tracing.setup()
store = Store(config)
llm = LLMClient(config)
attempt_log = AttemptLog(store)
flow = AnswerFlow(store, AnswerScorer(llm), QuestionRestater(llm), attempt_log)
app = FastAPI(title="Question-led learning")
app.state.learning = api.Learning(store, attempt_log, flow)
app.include_router(api.router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
