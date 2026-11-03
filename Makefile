.PHONY: check format demo evaluate package
PYTHON ?= python

check:
	$(PYTHON) -m ruff check src tests scripts
	$(PYTHON) -m ruff format --check src tests scripts
	$(PYTHON) -m unittest discover -s tests -v

format:
	$(PYTHON) -m ruff check --fix src tests scripts
	$(PYTHON) -m ruff format src tests scripts

demo:
	$(PYTHON) -m jumping_spyder demo

evaluate:
	$(PYTHON) -m jumping_spyder evaluate

package:
	$(PYTHON) -m build --no-isolation
	$(PYTHON) scripts/check_package.py dist/jumping_spyder-0.2.0-py3-none-any.whl
