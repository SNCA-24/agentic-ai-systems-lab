import os
from dotenv import load_dotenv

load_dotenv()


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CLASSIFIER_MODE = os.getenv("CLASSIFIER_MODE", "mock").lower()
APP_ENV = os.getenv("APP_ENV", "local").lower()
LANGSMITH_PROJECT_NAME = os.getenv(
    "LANGSMITH_PROJECT",
    "support-ticket-triage-agent",
)
LANGSMITH_RUN_TAG_PREFIX = os.getenv(
    "LANGSMITH_RUN_TAG_PREFIX",
    "support-ticket-triage",
)
