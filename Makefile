.PHONY: install check clean build pr clean-pyc

# Virtual environment settings
VENV := .venv

clean-pyc:
	@echo "Cleaning Python cache..."
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} +

install: clean-pyc
	@echo "Setting up development environment..."
	python3 -m venv $(VENV)
	# Install in the virtual environment (temporary activation)
	. $(VENV)/bin/activate && python -m pip install -e ".[dev]"
	@echo "\nVerifying installation:"
	@echo "Binary location: $(VENV)/bin/aimr"
	@echo "Python package location: $$($(VENV)/bin/python -c "import aimr; print(aimr.__file__)")"
	@echo "\nNext step:"
	@echo "To begin development, run: source .venv/bin/activate"
	@echo "This will activate the virtual environment in your shell"

format:
	. $(VENV)/bin/activate && python -m black aimr/ tests/
	. $(VENV)/bin/activate && python -m isort aimr/ tests/

lint:
	. $(VENV)/bin/activate && python -m flake8 aimr/ tests/

test:
	. $(VENV)/bin/activate && python -m pytest

check: format lint test
	@echo "\nAll checks passed!"
	@echo "Next step: Ready to commit your changes"

clean:
	@echo "Cleaning up build artifacts and virtual environment..."
	rm -rf dist/ build/ *.egg-info .coverage htmlcov/ .pytest_cache/ $(VENV)
	find . -name '__pycache__' -type d -exec rm -rf {} +
	@echo "\nNext step:"
	@echo "Run 'make install' to set up a fresh development environment"

build: clean
	. $(VENV)/bin/activate && python -m build

# GitHub PR target
# Usage: make pr title="Your PR title"
pr:
	@if [ -z "$(title)" ]; then \
		echo "Error: title parameter is required. Usage: make pr title=\"Your PR title\""; \
		exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: You have uncommitted changes. Please commit or stash them first."; \
		exit 1; \
	fi
	@if [ -n "$$(git log @{u}..)" ]; then \
		echo "Error: You have unpushed commits. Please push them first: git push"; \
		exit 1; \
	fi
	. $(VENV)/bin/activate && aimr -s --vulns -m azure/o1-mini -p meta | gh pr create --body-file - -t "$(title)"
	@echo "\nPull request created!"
	@echo "Next step: Wait for review and address any feedback" 