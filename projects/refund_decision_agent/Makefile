PYTHON := ./.venv/bin/python
PYTEST := ./.venv/bin/pytest

.PHONY: install test eval run-api check demo run-policy-demo seed-data

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTEST) -q

eval:
	$(PYTHON) -m evals.run_eval

run-api:
	$(PYTHON) -m uvicorn app.api:app --reload

demo:
	$(PYTHON) scripts/run_demo.py

run-policy-demo:
	$(PYTHON) scripts/run_policy_demo.py

seed-data:
	$(PYTHON) scripts/seed_data.py

check: test eval
