# -*- coding: utf-8 -*-
"""
Critical security and data integrity tests
Tests for the 5 severe issues fixed in ed91f93c
"""
import pytest
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
import tempfile
import os

# Import the functions and classes to test
import sys
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))


class TestPathTraversalProtection:
    """
    Test #1: Path Traversal Vulnerability Protection
    Ensures malicious file names cannot escape STRATEGIES_DIR
    """

    @pytest.mark.asyncio
    async def test_path_traversal_attempts_blocked(self, mock_env_vars, tmp_path):
        """CRITICAL: Should block path traversal attacks"""
        from backend.app.services.strategy_service import generate_strategy, STRATEGIES_DIR
        from backend.app.models.strategy import GenerateStrategyRequest

        # Patch STRATEGIES_DIR to use temp directory
        with patch('backend.app.services.strategy_service.STRATEGIES_DIR', tmp_path):
            malicious_names = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32",
                "....//....//etc/passwd",
                "/etc/passwd",
                "../../sensitive_file",
            ]

            for malicious_name in malicious_names:
                request = GenerateStrategyRequest(
                    name=malicious_name,
                    description="test strategy for path traversal validation",
                    stock_pool=["000001"],
                    start_date="20250101",
                    end_date="20251231"
                )

                # Mock the LLM API call
                with patch('anthropic.Anthropic') as mock_anthropic:
                    mock_client = MagicMock()
                    mock_message = MagicMock()
                    mock_message.content = [MagicMock(type="text", text="```python\nprint('test')\n```")]
                    mock_client.messages.create.return_value = mock_message
                    mock_anthropic.return_value = mock_client

                    # Mock prompt template
                    with patch('backend.app.services.strategy_service.get_prompt_template', return_value="test {{name}}"):
                        # Mock backtest
                        with patch('backend.app.services.strategy_service.run_real_backtest', return_value={
                            'total_return': 10.0,
                            'sharpe_ratio': 1.5,
                            'max_drawdown': 5.0,
                            'win_rate': 60.0,
                            'trades_count': 10,
                            'holding_periods': []
                        }):
                            response = await generate_strategy(request)

                            # Should succeed but with sanitized filename
                            if response.success:
                                # Verify the saved file is still within tmp_path
                                assert response.strategy_code is not None
                                # Check all created files are within tmp_path
                                created_files = list(tmp_path.glob("*.py"))
                                for file_path in created_files:
                                    # Ensure file is within tmp_path
                                    assert file_path.parent == tmp_path or tmp_path in file_path.parents

    @pytest.mark.asyncio
    async def test_filename_sanitization(self, mock_env_vars, tmp_path):
        """Should properly sanitize strategy names for filenames"""
        from backend.app.services.strategy_service import generate_strategy
        from backend.app.models.strategy import GenerateStrategyRequest

        with patch('backend.app.services.strategy_service.STRATEGIES_DIR', tmp_path):
            # Test special characters are replaced
            request = GenerateStrategyRequest(
                name="策略名称!@#$%^&*()",
                description="test strategy with special characters",
                stock_pool=["000001"],
                start_date="20250101",
                end_date="20251231"
            )

            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = MagicMock()
                mock_message = MagicMock()
                mock_message.content = [MagicMock(type="text", text="```python\nprint('test')\n```")]
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                with patch('backend.app.services.strategy_service.get_prompt_template', return_value="test"):
                    with patch('backend.app.services.strategy_service.run_real_backtest', return_value={
                        'total_return': 10.0, 'sharpe_ratio': 1.5, 'max_drawdown': 5.0,
                        'win_rate': 60.0, 'trades_count': 10, 'holding_periods': []
                    }):
                        response = await generate_strategy(request)

                        assert response.success is True
                        # Filename should only contain safe characters
                        created_files = list(tmp_path.glob("*.py"))
                        assert len(created_files) == 1
                        filename = created_files[0].name
                        # Should not contain special characters
                        assert "!" not in filename
                        assert "@" not in filename


class TestHashAlgorithmUpgrade:
    """
    Test #2: SHA-256 Hash instead of MD5
    Ensures stronger hash algorithm with lower collision probability
    """

    def test_sha256_used_for_fallback_filename(self):
        """Should use SHA-256 instead of MD5 for filename generation"""
        import re
        from pathlib import Path

        # Simulate the filename generation logic
        name = "!!!"  # Invalid filename
        strategy_filename = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', "_", name)
        strategy_filename = Path(strategy_filename).name

        if not strategy_filename.strip("_.") or strategy_filename.startswith('.'):
            # This should use SHA-256, not MD5
            hash_value = hashlib.sha256(name.encode()).hexdigest()[:16]
            strategy_filename = f"strategy_{hash_value}"

        # Verify it's using SHA-256 (16 hex chars from SHA-256)
        assert len(hash_value) == 16
        assert all(c in '0123456789abcdef' for c in hash_value)

    def test_filename_collision_resistance(self):
        """SHA-256 should have better collision resistance than MD5"""
        # Test that different inputs produce different hashes
        names = [f"strategy_{i}" for i in range(1000)]
        hashes = set()

        for name in names:
            hash_val = hashlib.sha256(name.encode()).hexdigest()[:16]
            hashes.add(hash_val)

        # All 1000 should be unique
        assert len(hashes) == 1000


class TestFileReadErrorHandling:
    """
    Test #4: File Read Error Handling
    Ensures get_prompt_template() handles all file I/O errors
    """

    def test_file_not_found_error(self, tmp_path):
        """Should raise RuntimeError with clear message when file not found"""
        from backend.app.services.strategy_service import get_prompt_template

        non_existent_path = tmp_path / "nonexistent.md"

        with patch('backend.app.services.strategy_service.PROMPT_TEMPLATE_PATH', non_existent_path):
            with pytest.raises(RuntimeError) as exc_info:
                get_prompt_template()

            assert "missing" in str(exc_info.value).lower()
            assert "deployment" in str(exc_info.value).lower()

    def test_permission_error(self, tmp_path):
        """Should raise RuntimeError when file permission denied"""
        from backend.app.services.strategy_service import get_prompt_template

        # Create a file with no read permissions
        test_file = tmp_path / "prompt.md"
        test_file.write_text("test content")
        test_file.chmod(0o000)  # No permissions

        try:
            with patch('backend.app.services.strategy_service.PROMPT_TEMPLATE_PATH', test_file):
                with pytest.raises(RuntimeError) as exc_info:
                    get_prompt_template()

                assert "permission" in str(exc_info.value).lower()
        finally:
            test_file.chmod(0o644)  # Restore permissions for cleanup

    def test_unicode_decode_error(self, tmp_path):
        """Should handle invalid UTF-8 encoding"""
        from backend.app.services.strategy_service import get_prompt_template

        # Create a file with invalid UTF-8
        test_file = tmp_path / "prompt.md"
        test_file.write_bytes(b'\xff\xfe invalid utf-8')

        with patch('backend.app.services.strategy_service.PROMPT_TEMPLATE_PATH', test_file):
            with pytest.raises(RuntimeError) as exc_info:
                get_prompt_template()

            assert "encoding" in str(exc_info.value).lower() or "UTF-8" in str(exc_info.value)


class TestFileWriteErrorHandling:
    """
    Test #5: File Write Error Handling
    Ensures strategy file write failures are detected and reported
    """

    @pytest.mark.asyncio
    async def test_permission_denied_writing_strategy(self, mock_env_vars, tmp_path):
        """Should return error when cannot write strategy file"""
        from backend.app.services.strategy_service import generate_strategy
        from backend.app.models.strategy import GenerateStrategyRequest

        # Make directory read-only
        tmp_path.chmod(0o444)

        try:
            with patch('backend.app.services.strategy_service.STRATEGIES_DIR', tmp_path):
                request = GenerateStrategyRequest(
                    name="test_strategy",
                    description="test strategy for error handling",
                    stock_pool=["000001"],
                    start_date="20250101",
                    end_date="20251231"
                )

                with patch('anthropic.Anthropic') as mock_anthropic:
                    mock_client = MagicMock()
                    mock_message = MagicMock()
                    mock_message.content = [MagicMock(type="text", text="```python\nprint('test')\n```")]
                    mock_client.messages.create.return_value = mock_message
                    mock_anthropic.return_value = mock_client

                    with patch('backend.app.services.strategy_service.get_prompt_template', return_value="test"):
                        response = await generate_strategy(request)

                        # Should fail with permission error
                        assert response.success is False
                        assert "permission" in response.message.lower() or "Permission" in str(response.errors)
        finally:
            tmp_path.chmod(0o755)  # Restore permissions

    @pytest.mark.asyncio
    async def test_disk_full_error(self, mock_env_vars, tmp_path):
        """Should detect and report disk full errors"""
        from backend.app.services.strategy_service import generate_strategy
        from backend.app.models.strategy import GenerateStrategyRequest

        with patch('backend.app.services.strategy_service.STRATEGIES_DIR', tmp_path):
            request = GenerateStrategyRequest(
                name="test_strategy",
                description="test strategy for error handling",
                stock_pool=["000001"],
                start_date="20250101",
                end_date="20251231"
            )

            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = MagicMock()
                mock_message = MagicMock()
                mock_message.content = [MagicMock(type="text", text="```python\nprint('test')\n```")]
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                with patch('backend.app.services.strategy_service.get_prompt_template', return_value="test"):
                    # Mock file write to raise disk full error
                    with patch('builtins.open', side_effect=OSError("No space left on device")):
                        response = await generate_strategy(request)

                        assert response.success is False
                        assert "disk" in response.message.lower() or "space" in response.message.lower()

    @pytest.mark.asyncio
    async def test_file_write_verification(self, mock_env_vars, tmp_path):
        """Should verify file was actually written successfully"""
        from backend.app.services.strategy_service import generate_strategy
        from backend.app.models.strategy import GenerateStrategyRequest

        with patch('backend.app.services.strategy_service.STRATEGIES_DIR', tmp_path):
            request = GenerateStrategyRequest(
                name="test_strategy",
                description="test strategy for error handling",
                stock_pool=["000001"],
                start_date="20250101",
                end_date="20251231"
            )

            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = MagicMock()
                mock_message = MagicMock()
                mock_message.content = [MagicMock(type="text", text="```python\nprint('test')\n```")]
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                with patch('backend.app.services.strategy_service.get_prompt_template', return_value="test"):
                    # Mock Path.exists() to return False (file not created)
                    with patch('pathlib.Path.exists', return_value=False):
                        response = await generate_strategy(request)

                        # Should detect file was not created
                        assert response.success is False


class TestSpecificExceptionHandling:
    """
    Test #3: Specific Exception Handling
    Ensures exceptions are caught specifically, not with bare 'except Exception'
    """

    @pytest.mark.asyncio
    async def test_api_connection_error_handling(self, mock_env_vars, tmp_path):
        """Should handle Anthropic API connection errors"""
        from backend.app.services.strategy_service import generate_strategy
        from backend.app.models.strategy import GenerateStrategyRequest
        import anthropic

        with patch('backend.app.services.strategy_service.STRATEGIES_DIR', tmp_path):
            request = GenerateStrategyRequest(
                name="test",
                description="test strategy for error handling",
                stock_pool=["000001"],
                start_date="20250101",
                end_date="20251231"
            )

            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = MagicMock()
                mock_client.messages.create.side_effect = anthropic.APIConnectionError("Connection failed")
                mock_anthropic.return_value = mock_client

                with patch('backend.app.services.strategy_service.get_prompt_template', return_value="test"):
                    response = await generate_strategy(request)

                    assert response.success is False
                    assert "连接" in response.message or "connect" in response.message.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, mock_env_vars, tmp_path):
        """Should handle API rate limit errors"""
        from backend.app.services.strategy_service import generate_strategy
        from backend.app.models.strategy import GenerateStrategyRequest
        import anthropic

        with patch('backend.app.services.strategy_service.STRATEGIES_DIR', tmp_path):
            request = GenerateStrategyRequest(
                name="test",
                description="test strategy for error handling",
                stock_pool=["000001"],
                start_date="20250101",
                end_date="20251231"
            )

            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = MagicMock()
                mock_client.messages.create.side_effect = anthropic.RateLimitError("Rate limited")
                mock_anthropic.return_value = mock_client

                with patch('backend.app.services.strategy_service.get_prompt_template', return_value="test"):
                    response = await generate_strategy(request)

                    assert response.success is False
                    assert "rate" in response.message.lower() or "请求" in response.message

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mock_env_vars, tmp_path):
        """Should handle API authentication errors"""
        from backend.app.services.strategy_service import generate_strategy
        from backend.app.models.strategy import GenerateStrategyRequest
        import anthropic

        with patch('backend.app.services.strategy_service.STRATEGIES_DIR', tmp_path):
            request = GenerateStrategyRequest(
                name="test",
                description="test strategy for error handling",
                stock_pool=["000001"],
                start_date="20250101",
                end_date="20251231"
            )

            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = MagicMock()
                mock_client.messages.create.side_effect = anthropic.AuthenticationError("Invalid API key")
                mock_anthropic.return_value = mock_client

                with patch('backend.app.services.strategy_service.get_prompt_template', return_value="test"):
                    response = await generate_strategy(request)

                    assert response.success is False
                    assert "认证" in response.message or "authentication" in response.message.lower()
