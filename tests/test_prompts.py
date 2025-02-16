import os

from aipr.prompts import PromptManager


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
