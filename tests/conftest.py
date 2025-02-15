"""
Shared test fixtures for AIMR
"""
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv('AZURE_API_KEY', 'test-key')
    monkeypatch.setenv('AZURE_API_BASE', 'test-base')
    monkeypatch.setenv('AZURE_API_VERSION', '2024-02-15-preview')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key')

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