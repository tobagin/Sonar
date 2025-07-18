"""
Tests for log retention policies.
"""

import logging
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.logging_config import (
    SonarLoggerConfig,
    configure_logging,
    configure_retention_policy,
    cleanup_logs,
    get_retention_info,
    reset_logging
)


class TestRetentionPolicies(unittest.TestCase):
    """Test log retention policies."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset logging configuration before each test
        reset_logging()

    def tearDown(self):
        """Clean up after each test."""
        # Reset logging configuration after each test
        reset_logging()

    def test_retention_policy_configuration(self):
        """Test retention policy configuration."""
        config = SonarLoggerConfig()
        
        # Test default values
        assert config._retention_days == 30
        assert config._max_total_size == 100 * 1024 * 1024
        assert config._cleanup_interval == 24 * 60 * 60
        assert config._cleanup_enabled == True
        
        # Configure retention policy
        config.configure_retention_policy(
            retention_days=7,
            max_total_size=50 * 1024 * 1024,
            cleanup_interval=12 * 60 * 60,
            enable_cleanup=False
        )
        
        assert config._retention_days == 7
        assert config._max_total_size == 50 * 1024 * 1024
        assert config._cleanup_interval == 12 * 60 * 60
        assert config._cleanup_enabled == False

    def test_retention_policy_in_configure(self):
        """Test retention policy parameters in configure method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'test.log'
            
            config = SonarLoggerConfig()
            config.configure(
                log_level='INFO',
                log_to_file=True,
                log_file_path=str(log_file),
                retention_days=14,
                max_total_size=200 * 1024 * 1024,
                cleanup_interval=6 * 60 * 60,
                enable_cleanup=True
            )
            
            assert config._retention_days == 14
            assert config._max_total_size == 200 * 1024 * 1024
            assert config._cleanup_interval == 6 * 60 * 60
            assert config._cleanup_enabled == True

    def test_log_file_detection(self):
        """Test log file detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test log files
            (log_dir / 'sonar.log').write_text('test log')
            (log_dir / 'sonar.log.1').write_text('old log')
            (log_dir / 'sonar.log.2').write_text('older log')
            (log_dir / 'other.log').write_text('other log')
            (log_dir / 'not_a_log.txt').write_text('not a log')
            
            config = SonarLoggerConfig()
            config._log_dir = log_dir
            
            log_files = config._get_log_files()
            log_names = [f.name for f in log_files]
            
            assert 'sonar.log' in log_names
            assert 'sonar.log.1' in log_names
            assert 'sonar.log.2' in log_names
            assert 'other.log' in log_names
            assert 'not_a_log.txt' not in log_names

    def test_total_size_calculation(self):
        """Test total size calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files with known sizes
            file1 = log_dir / 'test1.log'
            file2 = log_dir / 'test2.log'
            file1.write_text('a' * 1000)  # 1000 bytes
            file2.write_text('b' * 2000)  # 2000 bytes
            
            config = SonarLoggerConfig()
            total_size = config._get_total_size([file1, file2])
            
            assert total_size == 3000

    def test_cleanup_by_age(self):
        """Test cleanup by age."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files
            old_file = log_dir / 'old.log'
            new_file = log_dir / 'new.log'
            old_file.write_text('old log')
            new_file.write_text('new log')
            
            # Set old file to be very old
            old_time = time.time() - (40 * 24 * 60 * 60)  # 40 days ago
            os.utime(old_file, (old_time, old_time))
            
            config = SonarLoggerConfig()
            config._log_dir = log_dir
            config._retention_days = 30  # 30 days retention
            
            # Run cleanup
            config.cleanup_logs()
            
            # Check results
            assert not old_file.exists()  # Should be removed
            assert new_file.exists()      # Should remain

    def test_cleanup_by_size(self):
        """Test cleanup by total size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files
            file1 = log_dir / 'file1.log'
            file2 = log_dir / 'file2.log'
            file3 = log_dir / 'file3.log'
            
            file1.write_text('a' * 1000)
            file2.write_text('b' * 1000)
            file3.write_text('c' * 1000)
            
            # Set different modification times
            base_time = time.time()
            os.utime(file1, (base_time - 300, base_time - 300))  # Oldest
            os.utime(file2, (base_time - 200, base_time - 200))  # Middle
            os.utime(file3, (base_time - 100, base_time - 100))  # Newest
            
            config = SonarLoggerConfig()
            config._log_dir = log_dir
            config._retention_days = 365  # Keep all by age
            config._max_total_size = 2000  # Only allow 2000 bytes total
            
            # Run cleanup
            config.cleanup_logs()
            
            # Check results - oldest file should be removed
            assert not file1.exists()  # Should be removed (oldest)
            assert file2.exists()      # Should remain
            assert file3.exists()      # Should remain

    def test_get_retention_info(self):
        """Test get_retention_info method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files
            log_file = log_dir / 'test.log'
            log_file.write_text('test log content')
            
            config = SonarLoggerConfig()
            config._log_dir = log_dir
            config._retention_days = 15
            config._max_total_size = 50 * 1024 * 1024
            config._cleanup_interval = 12 * 60 * 60
            config._cleanup_enabled = True
            
            info = config.get_retention_info()
            
            assert info['retention_days'] == 15
            assert info['max_total_size'] == 50 * 1024 * 1024
            assert info['cleanup_interval'] == 12 * 60 * 60
            assert info['cleanup_enabled'] == True
            assert info['log_directory'] == str(log_dir)
            assert len(info['files']) == 1
            assert info['files'][0]['name'] == 'test.log'
            assert info['total_size'] > 0

    def test_force_cleanup(self):
        """Test force cleanup method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create old file
            old_file = log_dir / 'old.log'
            old_file.write_text('old log')
            
            # Set file to be old
            old_time = time.time() - (40 * 24 * 60 * 60)  # 40 days ago
            os.utime(old_file, (old_time, old_time))
            
            config = SonarLoggerConfig()
            config._log_dir = log_dir
            config._retention_days = 30
            
            # Force cleanup
            config.force_cleanup()
            
            # Check result
            assert not old_file.exists()

    @patch('threading.Thread')
    def test_cleanup_thread_management(self, mock_thread):
        """Test cleanup thread management."""
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        config = SonarLoggerConfig()
        config._log_dir = Path('/tmp')
        
        # Start cleanup thread
        config._start_cleanup_thread()
        
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        
        # Stop cleanup thread
        config._stop_cleanup_thread()
        
        assert config._cleanup_enabled == False
        mock_thread_instance.join.assert_called_once()

    def test_cleanup_with_no_log_dir(self):
        """Test cleanup when log directory doesn't exist."""
        config = SonarLoggerConfig()
        config._log_dir = None
        
        # Should not raise an exception
        config.cleanup_logs()
        
        # Test with non-existent directory
        config._log_dir = Path('/non/existent/path')
        config.cleanup_logs()

    def test_cleanup_with_permission_error(self):
        """Test cleanup with permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test file
            test_file = log_dir / 'test.log'
            test_file.write_text('test')
            
            config = SonarLoggerConfig()
            config._log_dir = log_dir
            
            # Mock unlink to raise permission error
            with patch.object(Path, 'unlink', side_effect=PermissionError("Permission denied")):
                # Should not raise exception
                config.cleanup_logs()


class TestGlobalRetentionFunctions(unittest.TestCase):
    """Test global retention functions."""

    def setUp(self):
        """Set up test fixtures."""
        reset_logging()

    def tearDown(self):
        """Clean up after each test."""
        reset_logging()

    def test_configure_retention_policy(self):
        """Test configure_retention_policy function."""
        configure_retention_policy(
            retention_days=7,
            max_total_size=50 * 1024 * 1024,
            cleanup_interval=6 * 60 * 60,
            enable_cleanup=False
        )
        
        info = get_retention_info()
        assert info['retention_days'] == 7
        assert info['max_total_size'] == 50 * 1024 * 1024
        assert info['cleanup_interval'] == 6 * 60 * 60
        assert info['cleanup_enabled'] == False

    def test_get_retention_info(self):
        """Test get_retention_info function."""
        configure_retention_policy(retention_days=14)
        
        info = get_retention_info()
        assert isinstance(info, dict)
        assert 'retention_days' in info
        assert 'max_total_size' in info
        assert info['retention_days'] == 14

    def test_cleanup_logs_function(self):
        """Test cleanup_logs function."""
        # Should not raise exception even if not configured
        cleanup_logs()

    def test_configure_logging_with_retention(self):
        """Test configure_logging with retention parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'test.log'
            
            configure_logging(
                log_level='INFO',
                log_to_file=True,
                log_file_path=str(log_file),
                retention_days=21,
                max_total_size=75 * 1024 * 1024,
                cleanup_interval=18 * 60 * 60,
                enable_cleanup=True
            )
            
            info = get_retention_info()
            assert info['retention_days'] == 21
            assert info['max_total_size'] == 75 * 1024 * 1024
            assert info['cleanup_interval'] == 18 * 60 * 60
            assert info['cleanup_enabled'] == True


if __name__ == '__main__':
    unittest.main()