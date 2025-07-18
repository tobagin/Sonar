"""
Tests for log compression functionality.
"""

import gzip
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
    decompress_log_file,
    get_retention_info,
    reset_logging
)


class TestLogCompression(unittest.TestCase):
    """Test log compression functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset logging configuration before each test
        reset_logging()

    def tearDown(self):
        """Clean up after each test."""
        # Reset logging configuration after each test
        reset_logging()

    def test_compression_configuration(self):
        """Test compression configuration."""
        config = SonarLoggerConfig()
        
        # Test default values
        assert config._compression_enabled == True
        assert config._compression_age_days == 7
        assert config._compression_format == 'gzip'
        
        # Configure compression
        config.configure_retention_policy(
            compression_enabled=False,
            compression_age_days=14
        )
        
        assert config._compression_enabled == False
        assert config._compression_age_days == 14

    def test_compression_in_configure(self):
        """Test compression parameters in configure method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'test.log'
            
            config = SonarLoggerConfig()
            config.configure(
                log_level='INFO',
                log_to_file=True,
                log_file_path=str(log_file),
                compression_enabled=True,
                compression_age_days=3
            )
            
            assert config._compression_enabled == True
            assert config._compression_age_days == 3

    def test_compress_file_success(self):
        """Test successful file compression."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test log file
            test_file = log_dir / 'test.log'
            test_content = 'This is a test log file with some content.'
            test_file.write_text(test_content)
            
            # Store original modification time
            original_stat = test_file.stat()
            
            config = SonarLoggerConfig()
            
            # Compress the file
            result = config._compress_file(test_file)
            
            # Check results
            assert result == True
            assert not test_file.exists()  # Original file should be removed
            
            compressed_file = log_dir / 'test.log.gz'
            assert compressed_file.exists()  # Compressed file should exist
            
            # Verify compressed file contents
            with gzip.open(compressed_file, 'rt') as f:
                decompressed_content = f.read()
            assert decompressed_content == test_content
            
            # Verify modification time was preserved
            compressed_stat = compressed_file.stat()
            assert abs(compressed_stat.st_mtime - original_stat.st_mtime) < 1

    def test_compress_file_already_exists(self):
        """Test compression when compressed file already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test log file
            test_file = log_dir / 'test.log'
            test_file.write_text('test content')
            
            # Create compressed file that already exists
            compressed_file = log_dir / 'test.log.gz'
            compressed_file.write_text('existing compressed file')
            
            config = SonarLoggerConfig()
            
            # Try to compress the file
            result = config._compress_file(test_file)
            
            # Should return False and not modify anything
            assert result == False
            assert test_file.exists()  # Original file should remain
            assert compressed_file.exists()  # Compressed file should remain

    def test_compress_file_error_handling(self):
        """Test compression error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test log file
            test_file = log_dir / 'test.log'
            test_file.write_text('test content')
            
            config = SonarLoggerConfig()
            
            # Mock gzip.open to raise an exception
            with patch('gzip.open', side_effect=Exception('Compression error')):
                result = config._compress_file(test_file)
                
                # Should return False and handle the error gracefully
                assert result == False
                assert test_file.exists()  # Original file should remain

    def test_compress_old_files(self):
        """Test compression of old files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files
            old_file = log_dir / 'old.log'
            new_file = log_dir / 'new.log'
            already_compressed = log_dir / 'compressed.log.gz'
            active_file = log_dir / 'sonar.log'
            
            old_file.write_text('old log content')
            new_file.write_text('new log content')
            already_compressed.write_text('already compressed')
            active_file.write_text('active log content')
            
            # Set file modification times
            old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days old
            new_time = time.time() - (1 * 24 * 60 * 60)   # 1 day old
            
            os.utime(old_file, (old_time, old_time))
            os.utime(new_file, (new_time, new_time))
            os.utime(already_compressed, (old_time, old_time))
            os.utime(active_file, (new_time, new_time))
            
            config = SonarLoggerConfig()
            config._compression_enabled = True
            config._compression_age_days = 7  # Compress files older than 7 days
            
            # Run compression
            files_compressed = config._compress_old_files([old_file, new_file, already_compressed, active_file])
            
            # Check results
            assert files_compressed == 1  # Only old.log should be compressed
            assert not old_file.exists()  # Old file should be removed
            assert (log_dir / 'old.log.gz').exists()  # Compressed file should exist
            assert new_file.exists()  # New file should remain
            assert already_compressed.exists()  # Already compressed file should remain
            assert active_file.exists()  # Active file should remain

    def test_compress_old_files_disabled(self):
        """Test compression when disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create old file
            old_file = log_dir / 'old.log'
            old_file.write_text('old log content')
            
            # Set file to be old
            old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days old
            os.utime(old_file, (old_time, old_time))
            
            config = SonarLoggerConfig()
            config._compression_enabled = False  # Disable compression
            
            # Run compression
            files_compressed = config._compress_old_files([old_file])
            
            # Check results
            assert files_compressed == 0  # No files should be compressed
            assert old_file.exists()  # File should remain

    def test_decompress_file_success(self):
        """Test successful file decompression."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test content
            test_content = 'This is test log content for decompression.'
            
            # Create compressed file
            compressed_file = log_dir / 'test.log.gz'
            with gzip.open(compressed_file, 'wt') as f:
                f.write(test_content)
            
            # Store original modification time
            original_stat = compressed_file.stat()
            
            config = SonarLoggerConfig()
            
            # Decompress the file
            result = config.decompress_file(compressed_file)
            
            # Check results
            assert result == True
            
            decompressed_file = log_dir / 'test.log'
            assert decompressed_file.exists()  # Decompressed file should exist
            
            # Verify decompressed content
            assert decompressed_file.read_text() == test_content
            
            # Verify modification time was preserved
            decompressed_stat = decompressed_file.stat()
            assert abs(decompressed_stat.st_mtime - original_stat.st_mtime) < 1

    def test_decompress_file_custom_output(self):
        """Test decompression with custom output file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test content
            test_content = 'Test content for custom output.'
            
            # Create compressed file
            compressed_file = log_dir / 'test.log.gz'
            with gzip.open(compressed_file, 'wt') as f:
                f.write(test_content)
            
            # Custom output file
            output_file = log_dir / 'custom_output.log'
            
            config = SonarLoggerConfig()
            
            # Decompress with custom output
            result = config.decompress_file(compressed_file, output_file)
            
            # Check results
            assert result == True
            assert output_file.exists()  # Custom output file should exist
            assert output_file.read_text() == test_content

    def test_decompress_file_already_exists(self):
        """Test decompression when output file already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create compressed file
            compressed_file = log_dir / 'test.log.gz'
            with gzip.open(compressed_file, 'wt') as f:
                f.write('test content')
            
            # Create output file that already exists
            output_file = log_dir / 'test.log'
            output_file.write_text('existing content')
            
            config = SonarLoggerConfig()
            
            # Try to decompress
            result = config.decompress_file(compressed_file)
            
            # Should return False and not modify anything
            assert result == False
            assert output_file.read_text() == 'existing content'

    def test_decompress_file_error_handling(self):
        """Test decompression error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create compressed file
            compressed_file = log_dir / 'test.log.gz'
            with gzip.open(compressed_file, 'wt') as f:
                f.write('test content')
            
            config = SonarLoggerConfig()
            
            # Mock gzip.open to raise an exception
            with patch('gzip.open', side_effect=Exception('Decompression error')):
                result = config.decompress_file(compressed_file)
                
                # Should return False and handle the error gracefully
                assert result == False

    def test_cleanup_with_compression(self):
        """Test cleanup process with compression enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files
            old_file = log_dir / 'old.log'
            very_old_file = log_dir / 'very_old.log'
            new_file = log_dir / 'new.log'
            
            old_file.write_text('old log content')
            very_old_file.write_text('very old log content')
            new_file.write_text('new log content')
            
            # Set file modification times
            current_time = time.time()
            old_time = current_time - (10 * 24 * 60 * 60)  # 10 days old (should be compressed)
            very_old_time = current_time - (40 * 24 * 60 * 60)  # 40 days old (should be removed)
            new_time = current_time - (1 * 24 * 60 * 60)   # 1 day old (should remain)
            
            os.utime(old_file, (old_time, old_time))
            os.utime(very_old_file, (very_old_time, very_old_time))
            os.utime(new_file, (new_time, new_time))
            
            config = SonarLoggerConfig()
            config._log_dir = log_dir
            config._compression_enabled = True
            config._compression_age_days = 7  # Compress files older than 7 days
            config._retention_days = 30  # Remove files older than 30 days
            
            # Run cleanup
            config.cleanup_logs()
            
            # Check results
            assert not old_file.exists()  # Should be compressed
            assert (log_dir / 'old.log.gz').exists()  # Compressed file should exist
            assert not very_old_file.exists()  # Should be removed due to age
            assert new_file.exists()  # Should remain

    def test_retention_info_with_compression(self):
        """Test retention info includes compression statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files
            regular_file = log_dir / 'regular.log'
            compressed_file = log_dir / 'compressed.log.gz'
            
            regular_file.write_text('regular log content')
            with gzip.open(compressed_file, 'wt') as f:
                f.write('compressed log content')
            
            config = SonarLoggerConfig()
            config._log_dir = log_dir
            config._compression_enabled = True
            config._compression_age_days = 7
            
            # Get retention info
            info = config.get_retention_info()
            
            # Check compression information
            assert 'compression_enabled' in info
            assert 'compression_age_days' in info
            assert 'compressed_files' in info
            assert 'uncompressed_files' in info
            
            assert info['compression_enabled'] == True
            assert info['compression_age_days'] == 7
            assert info['compressed_files'] == 1
            assert info['uncompressed_files'] == 1


class TestGlobalCompressionFunctions(unittest.TestCase):
    """Test global compression functions."""

    def setUp(self):
        """Set up test fixtures."""
        reset_logging()

    def tearDown(self):
        """Clean up after each test."""
        reset_logging()

    def test_configure_logging_with_compression(self):
        """Test configure_logging with compression parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'test.log'
            
            configure_logging(
                log_level='INFO',
                log_to_file=True,
                log_file_path=str(log_file),
                compression_enabled=True,
                compression_age_days=14
            )
            
            info = get_retention_info()
            assert info['compression_enabled'] == True
            assert info['compression_age_days'] == 14

    def test_configure_retention_policy_with_compression(self):
        """Test configure_retention_policy with compression parameters."""
        configure_retention_policy(
            compression_enabled=False,
            compression_age_days=21
        )
        
        info = get_retention_info()
        assert info['compression_enabled'] == False
        assert info['compression_age_days'] == 21

    def test_decompress_log_file_function(self):
        """Test decompress_log_file function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test content
            test_content = 'Test content for global decompression function.'
            
            # Create compressed file
            compressed_file = log_dir / 'test.log.gz'
            with gzip.open(compressed_file, 'wt') as f:
                f.write(test_content)
            
            # Test decompression
            result = decompress_log_file(str(compressed_file))
            
            # Check results
            assert result == True
            
            decompressed_file = log_dir / 'test.log'
            assert decompressed_file.exists()
            assert decompressed_file.read_text() == test_content

    def test_decompress_log_file_with_custom_output(self):
        """Test decompress_log_file with custom output path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test content
            test_content = 'Test content for custom output.'
            
            # Create compressed file
            compressed_file = log_dir / 'test.log.gz'
            with gzip.open(compressed_file, 'wt') as f:
                f.write(test_content)
            
            # Custom output file
            output_file = log_dir / 'custom.log'
            
            # Test decompression with custom output
            result = decompress_log_file(str(compressed_file), str(output_file))
            
            # Check results
            assert result == True
            assert output_file.exists()
            assert output_file.read_text() == test_content


if __name__ == '__main__':
    unittest.main()