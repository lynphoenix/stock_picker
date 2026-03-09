# -*- coding: utf-8 -*-
"""
Pytest configuration and fixtures
"""
import sys
import pytest
from pathlib import Path

# Add project root to Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://test.example.com")
    monkeypatch.setenv("ANTHROPIC_MODEL", "test-model")


@pytest.fixture
def temp_strategies_dir(tmp_path):
    """Create a temporary strategies directory"""
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    return strategies_dir


@pytest.fixture
def temp_prompt_file(tmp_path):
    """Create a temporary prompt template file"""
    prompt_file = tmp_path / "prompts" / "strategy_generation_prompt.md"
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("Strategy prompt: {{name}} - {{description}}")
    return prompt_file
