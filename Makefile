PYTHON ?= python3.6

PIP=$(PYTHON) -m pip
PYTEST=$(PYTHON) -m pytest

.PHONY: install-deps
install-deps:
	$(PIP) install -r requirements/local.txt

.PHONY: test
test:
	$(PYTEST) eas --cov=eas --cov-report=term-missing --cov-fail-under=100 -vv

.PHONY: lint
lint:
	DJANGO_SETTINGS_MODULE=eas.settings.local $(PYTHON) -m pylint eas
	$(PYTHON) -m isort eas --check --recursive
	$(PYTHON) -m black eas --check

.PHONY: format
format:
	$(PYTHON) -m isort eas --recursive
	$(PYTHON) -m black eas

.PHONY: runlocal
runlocal:
	$(PYTHON) ./manage.py migrate
	$(PYTHON) ./manage.py runserver

.PHONY: check-frozen-reqs
check-frozen-reqs:
	pip-compile requirements/base.txt requirements/base.orig.txt --output-file=requirements/base.txt --quiet --no-annotate
	git diff --exit-code
