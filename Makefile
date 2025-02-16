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
	@echo "Binary location: $(VENV)/bin/aipr"
	@echo "Python package location: $$($(VENV)/bin/python -c "import aipr; print(aipr.__file__)")"
	@echo "\nNext step:"
	@echo "To begin development, run: source .venv/bin/activate"
	@echo "This will activate the virtual environment in your shell"

format:
	. $(VENV)/bin/activate && python -m black aipr/ tests/
	. $(VENV)/bin/activate && python -m isort aipr/ tests/

lint:
	. $(VENV)/bin/activate && python -m flake8 aipr/ tests/

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
	@echo "Run 'deactivate' to ensure python is not running in the virtual environment"

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
	@BRANCH=$$(git branch --show-current); \
	if ! git show-ref --verify --quiet refs/remotes/origin/$$BRANCH; then \
		if git ls-remote --exit-code --heads origin $$BRANCH >/dev/null 2>&1; then \
			git branch --set-upstream-to=origin/$$BRANCH $$BRANCH 2>/dev/null || true; \
		else \
			echo "Error: Branch '$$BRANCH' does not exist on remote 'origin'."; \
			echo "Please push the branch with: git push --set-upstream origin $$BRANCH"; \
			exit 1; \
		fi; \
	fi
	@if [ -n "$$(git log @{u}.. 2>/dev/null)" ]; then \
		echo "Error: You have unpushed commits. Please push them first: git push"; \
		exit 1; \
	fi
	@BRANCH=$$(git branch --show-current); \
	PR_COUNT=$$(gh pr list --head $$BRANCH --state open --json number --jq 'length'); \
	if [ "$$PR_COUNT" -gt 0 ]; then \
		echo "Updating existing pull request for branch $$BRANCH..."; \
		. $(VENV)/bin/activate && aipr -s --vulns -m azure/o1-mini -p meta | gh pr edit $$BRANCH --body-file -; \
		echo "\nPull request updated!"; \
		echo "Next step: Address any new feedback"; \
	else \
		echo "Creating new pull request for branch $$BRANCH..."; \
		. $(VENV)/bin/activate && aipr -s --vulns -m azure/o1-mini -p meta | gh pr create --body-file - -t "$(title)"; \
		echo "\nPull request created!"; \
		echo "Next step: Wait for review and address any feedback"; \
	fi