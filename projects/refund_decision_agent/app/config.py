import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=PROJECT_DIR / ".env")

DATA_DIR = PROJECT_DIR / "data"
POLICY_DIR = DATA_DIR / "policies"
CUSTOMERS_PATH = DATA_DIR / "mock_customers.json"
BILLING_RECORDS_PATH = DATA_DIR / "mock_billing_records.json"
DECISION_RECORDS_PATH = DATA_DIR / "decision_records.json"

APP_ENV = os.getenv("APP_ENV", "local").lower()
CLASSIFIER_MODE = os.getenv("CLASSIFIER_MODE", "mock").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "refund-decision-agent")
