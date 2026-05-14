import os
from dotenv import load_dotenv

load_dotenv()


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CLASSIFIER_MODE = os.getenv("CLASSIFIER_MODE", "mock").lower()