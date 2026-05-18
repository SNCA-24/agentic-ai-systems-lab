

.PHONY: install test eval check run-api demo-interrupt demo-api compile clean

PYTHON := python
PIP := pip
UVICORN := uvicorn

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

test:
	pytest

eval:
	$(PYTHON) -m evals.run_eval

check: compile test eval

compile:
	$(PYTHON) -m py_compile main.py
	$(PYTHON) -m py_compile app/*.py
	$(PYTHON) -m py_compile scripts/demo_interruptible_graph.py

run-api:
	$(UVICORN) app.api:app --reload

demo-interrupt:
	$(PYTHON) scripts/demo_interruptible_graph.py

demo-api:
	zsh scripts/demo_checkpointed_api.sh

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete