"""
Shared test fixtures for AIPR
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock environment variables for testing"""
    # Azure OpenAI settings
    monkeypatch.setenv("AZURE_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_API_BASE", "test-base")
    monkeypatch.setenv("AZURE_API_VERSION", "2024-02-15-preview")
    # OpenAI settings
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    # Anthropic settings
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture
def mock_diff():
    """Sample git diff for testing"""
    return """
diff --git a/test.py b/test.py
index 1234567..89abcdef 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
+import os
 def test_function():
-    return False
+    return True
"""


@pytest.fixture
def mock_repo():
    """Create a mock git repository for testing"""
    mock = MagicMock()
    mock.active_branch.name = "feature-branch"
    mock.index.diff.return_value = []  # No staged changes by default
    mock.untracked_files = []  # No untracked files by default
    mock.heads = [MagicMock(name="main"), MagicMock(name="feature-branch")]
    # Make branch names accessible via name attribute
    for head in mock.heads:
        head.name = head._mock_name
    mock.git.diff.return_value = "test diff content"
    return mock
