"""
Tests for the centralized logging configuration.
"""

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.logging_config import (
    SonarLoggerConfig,
    configure_logging,
    get_logger,
    set_log_level,
    add_file_logging,
    remove_file_logging,
    get_current_level,
    is_configured,
    get_log_directory,
    reset_logging
)


class TestSonarLoggerConfig(unittest.TestCase):
    """Test SonarLoggerConfig class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset logging configuration before each test
        reset_logging()

    def tearDown(self):
        """Clean up after each test."""
        # Reset logging configuration after each test
        reset_logging()

    def test_logger_config_initialization(self):
        """Test logger config initialization."""
        config = SonarLoggerConfig()
        
        assert not config.is_configured()
        assert config.get_current_level() == 'INFO'
        assert config.get_log_directory() is None

    def test_basic_configuration(self):
        """Test basic logging configuration."""
        config = SonarLoggerConfig()
        config.configure(
            log_level='DEBUG',
            console_logging=True,
            log_to_file=False
        )
        
        assert config.is_configured()
        assert config.get_current_level() == 'DEBUG'
        
        # Test that logger works
        logger = config.get_logger(__name__)
        # Individual loggers inherit from root logger, so level should be 0 (NOTSET)
        assert logger.level == 0  # NOTSET means inherit from root
        
        # Test that root logger has the correct level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_file_logging_configuration(self):
        """Test file logging configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'test.log'
            
            config = SonarLoggerConfig()
            config.configure(
                log_level='INFO',
                log_to_file=True,
                log_file_path=str(log_file),
                console_logging=False
            )
            
            assert config.is_configured()
            assert log_file.exists()
            
            # Test logging to file
            logger = config.get_logger(__name__)
            logger.info("Test message")
            
            # Check that message was written to file
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test message" in content

    def test_log_level_change(self):
        """Test changing log level at runtime."""
        config = SonarLoggerConfig()
        config.configure(log_level='INFO')
        
        assert config.get_current_level() == 'INFO'
        
        config.set_level('DEBUG')
        assert config.get_current_level() == 'DEBUG'
        
        config.set_level('ERROR')
        assert config.get_current_level() == 'ERROR'

    def test_add_remove_file_logging(self):
        """Test adding and removing file logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'test.log'
            
            config = SonarLoggerConfig()
            config.configure(log_level='INFO', console_logging=True, log_to_file=False)
            
            # Add file logging
            config.add_file_logging(str(log_file))
            assert log_file.exists()
            
            # Test logging
            logger = config.get_logger(__name__)
            logger.info("Test file logging")
            
            # Remove file logging
            config.remove_file_logging()
            
            # Verify file still exists but no more logging
            assert log_file.exists()

    def test_detailed_logging_format(self):
        """Test detailed logging format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'detailed.log'
            
            config = SonarLoggerConfig()
            config.configure(
                log_level='DEBUG',
                log_to_file=True,
                log_file_path=str(log_file),
                detailed_logging=True,
                console_logging=False
            )
            
            logger = config.get_logger(__name__)
            logger.info("Detailed test message")
            
            # Check that detailed format is used
            with open(log_file, 'r') as f:
                content = f.read()
                assert "test_logging_config.py" in content  # filename
                assert "test_detailed_logging_format" in content  # function name

    def test_log_rotation(self):
        """Test log file rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'rotation.log'
            
            config = SonarLoggerConfig()
            config.configure(
                log_level='INFO',
                log_to_file=True,
                log_file_path=str(log_file),
                max_file_size=100,  # Very small size to trigger rotation
                backup_count=2,
                console_logging=False
            )
            
            logger = config.get_logger(__name__)
            
            # Generate enough log messages to trigger rotation
            for i in range(100):
                logger.info(f"Log message {i} - this is a long message to fill up the log file")
            
            # Check that rotation occurred
            assert log_file.exists()
            # Note: Actual rotation testing would require more complex setup


class TestGlobalFunctions(unittest.TestCase):
    """Test global logging functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset logging configuration
        reset_logging()

    def tearDown(self):
        """Clean up after each test."""
        # Reset logging configuration
        reset_logging()

    def test_configure_logging(self):
        """Test configure_logging function."""
        configure_logging(
            log_level='DEBUG',
            console_logging=True,
            log_to_file=False
        )
        
        assert is_configured()
        assert get_current_level() == 'DEBUG'

    def test_get_logger(self):
        """Test get_logger function."""
        configure_logging(log_level='INFO')
        
        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)
        assert logger.name == __name__

    def test_set_log_level(self):
        """Test set_log_level function."""
        configure_logging(log_level='INFO')
        
        assert get_current_level() == 'INFO'
        
        set_log_level('DEBUG')
        assert get_current_level() == 'DEBUG'

    def test_file_logging_functions(self):
        """Test add_file_logging and remove_file_logging functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'function_test.log'
            
            configure_logging(log_level='INFO', console_logging=True, log_to_file=False)
            
            # Add file logging
            add_file_logging(str(log_file))
            assert log_file.exists()
            
            # Test logging
            logger = get_logger(__name__)
            logger.info("Function test message")
            
            # Remove file logging
            remove_file_logging()
            
            # Verify file still exists
            assert log_file.exists()

    def test_get_log_directory(self):
        """Test get_log_directory function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'dir_test.log'
            
            configure_logging(
                log_level='INFO',
                log_to_file=True,
                log_file_path=str(log_file),
                console_logging=False
            )
            
            log_dir = get_log_directory()
            assert log_dir == Path(temp_dir)

    def test_invalid_log_level(self):
        """Test handling of invalid log level."""
        configure_logging(log_level='INVALID')
        
        # Should default to INFO
        assert get_current_level() == 'INFO'
        
        set_log_level('INVALID')
        
        # Should remain at INFO
        assert get_current_level() == 'INFO'


if __name__ == '__main__':
    unittest.main()