"""Tests for the prompt manager functionality."""

import os
import tempfile
from pathlib import Path

import pytest

from aipr.prompts.prompts import InvalidPromptError, PromptManager


def create_test_prompt(content: str) -> Path:
    """Create a temporary prompt file with the given content."""
    fd, path = tempfile.mkstemp(suffix=".xml")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return Path(path)


def test_load_valid_custom_prompt():
    """Test loading a valid custom prompt file."""
    content = """<?xml version="1.0" encoding="UTF-8"?>
    <prompt>
        <changes-set></changes-set>
        <vulnerabilities-set></vulnerabilities-set>
    </prompt>
    """
    prompt_file = create_test_prompt(content)
    try:
        manager = PromptManager(str(prompt_file))
        assert manager._xml_prompt is not None
    finally:
        prompt_file.unlink()


def test_load_invalid_custom_prompt():
    """Test loading an invalid custom prompt file."""
    content = """<?xml version="1.0" encoding="UTF-8"?>
    <prompt>
        <changes-set></changes-set>
        <!-- Missing vulnerabilities-set -->
    </prompt>
    """
    prompt_file = create_test_prompt(content)
    try:
        with pytest.raises(InvalidPromptError) as exc_info:
            PromptManager(str(prompt_file))
        assert "Missing required element 'vulnerabilities-set'" in str(exc_info.value)
    finally:
        prompt_file.unlink()


def test_load_nonexistent_prompt():
    """Test loading a nonexistent prompt file."""
    nonexistent_path = "/nonexistent/path/to/prompt.xml"
    with pytest.raises(InvalidPromptError) as exc_info:
        PromptManager(nonexistent_path)
    error_msg = str(exc_info.value)
    assert "Prompt file not found:" in error_msg
    assert nonexistent_path in error_msg


def test_load_malformed_xml():
    """Test loading a malformed XML file."""
    content = """<?xml version="1.0" encoding="UTF-8"?>
    <prompt>
        <changes-set></changes-set
        <vulnerabilities-set></vulnerabilities-set>
    </prompt>
    """
    prompt_file = create_test_prompt(content)
    try:
        with pytest.raises(InvalidPromptError) as exc_info:
            PromptManager(str(prompt_file))
        assert "Error parsing XML prompt file" in str(exc_info.value)
    finally:
        prompt_file.unlink()


def test_load_builtin_prompt():
    """Test loading a built-in prompt."""
    manager = PromptManager("meta")
    assert manager._xml_prompt is not None


def test_load_invalid_builtin_prompt():
    """Test loading an invalid built-in prompt name."""
    with pytest.raises(InvalidPromptError) as exc_info:
        PromptManager("nonexistent_prompt")
    assert "Could not load prompt 'nonexistent_prompt'" in str(exc_info.value)
    assert "Available built-in prompts" in str(exc_info.value)


def test_prompt_manager_initialization():
    """Test PromptManager initializes correctly"""
    manager = PromptManager()
    assert manager is not None
    assert isinstance(manager._default_system_prompt, str)


def test_get_system_prompt():
    """Test system prompt generation"""
    manager = PromptManager()
    system_prompt = manager.get_system_prompt()
    assert "You are a helpful assistant for generating Merge Requests" in system_prompt
    assert "Your task is to analyze Git changes" in system_prompt


def test_get_user_prompt():
    """Test user prompt generation"""
    manager = PromptManager()
    diff = "test diff content"
    vuln_data = "test vulnerability data"

    # Test with diff only
    user_prompt = manager.get_user_prompt(diff)
    assert diff in user_prompt
    assert "Git Diff:" in user_prompt
    assert "Vulnerability Analysis:" not in user_prompt

    # Test with both diff and vulnerability data
    user_prompt = manager.get_user_prompt(diff, vuln_data)
    assert diff in user_prompt
    assert vuln_data in user_prompt
    assert "Git Diff:" in user_prompt
    assert "Vulnerability Analysis:" in user_prompt
