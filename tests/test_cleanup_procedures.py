"""
Tests for cleanup procedures functionality.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from src.logging_config import (
    cleanup_logs_by_age,
    cleanup_logs_by_size,
    compress_all_logs,
    get_cleanup_statistics,
    emergency_cleanup,
    reset_logging
)


class TestCleanupProcedures(unittest.TestCase):
    """Test cleanup procedures functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset logging configuration before each test
        reset_logging()

    def tearDown(self):
        """Clean up after each test."""
        # Reset logging configuration after each test
        reset_logging()

    def test_cleanup_logs_by_age(self):
        """Test cleanup by age functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files with different ages
            old_file = log_dir / 'old.log'
            new_file = log_dir / 'new.log'
            old_file.write_text('old log content')
            new_file.write_text('new log content')
            
            # Set different modification times
            old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days old
            new_time = time.time() - (1 * 24 * 60 * 60)   # 1 day old
            
            os.utime(old_file, (old_time, old_time))
            os.utime(new_file, (new_time, new_time))
            
            # Mock the global config to use our test directory
            with patch('src.logging_config._get_global_config') as mock_config:
                mock_instance = mock_config.return_value
                mock_instance._log_dir = log_dir
                mock_instance._get_log_files.return_value = [old_file, new_file]
                
                # Test cleanup with 7 days retention
                result = cleanup_logs_by_age(7)
                
                # Should remove the old file
                assert result['files_removed'] == 1
                assert result['cutoff_days'] == 7
                assert result['size_freed'] > 0
                assert not old_file.exists()
                assert new_file.exists()

    def test_cleanup_logs_by_size(self):
        """Test cleanup by size functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files with known sizes
            file1 = log_dir / 'file1.log'
            file2 = log_dir / 'file2.log'
            file3 = log_dir / 'file3.log'
            
            file1.write_text('a' * 1000)  # 1KB
            file2.write_text('b' * 1000)  # 1KB
            file3.write_text('c' * 1000)  # 1KB
            
            # Set different modification times (file1 is oldest)
            base_time = time.time()
            os.utime(file1, (base_time - 300, base_time - 300))
            os.utime(file2, (base_time - 200, base_time - 200))
            os.utime(file3, (base_time - 100, base_time - 100))
            
            # Mock the global config
            with patch('src.logging_config._get_global_config') as mock_config:
                mock_instance = mock_config.return_value
                mock_instance._log_dir = log_dir
                mock_instance._get_log_files.return_value = [file1, file2, file3]
                
                # Mock _get_total_size to return size that's over the limit
                mock_instance._get_total_size.return_value = 3 * 1024 * 1024  # 3MB
                
                # Test cleanup with 2MB limit (should try to remove files)
                result = cleanup_logs_by_size(2)  # 2MB limit
                
                # Should report cleanup attempt
                assert result['max_size_mb'] == 2
                assert 'files_removed' in result
                assert 'size_freed' in result

    def test_compress_all_logs(self):
        """Test compress all logs functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files
            log_file1 = log_dir / 'test1.log'
            log_file2 = log_dir / 'test2.log'
            active_file = log_dir / 'sonar.log'
            compressed_file = log_dir / 'test3.log.gz'
            
            log_file1.write_text('test log content 1')
            log_file2.write_text('test log content 2')
            active_file.write_text('active log content')
            compressed_file.write_text('already compressed')
            
            # Mock the global config
            with patch('src.logging_config._get_global_config') as mock_config:
                mock_instance = mock_config.return_value
                mock_instance._log_dir = log_dir
                mock_instance._get_log_files.return_value = [log_file1, log_file2, active_file, compressed_file]
                
                # Mock compression to succeed
                def mock_compress_file(file_path):
                    if file_path.name != 'sonar.log':
                        return True
                    return False
                
                mock_instance._compress_file.side_effect = mock_compress_file
                
                # Test compress all
                result = compress_all_logs()
                
                # Should compress log_file1 and log_file2, skip active and already compressed
                assert result['files_compressed'] == 2
                assert result['total_candidates'] == 3  # log_file1, log_file2, active_file
                assert result['size_saved'] > 0

    def test_get_cleanup_statistics(self):
        """Test get cleanup statistics functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files with different ages and types
            recent_file = log_dir / 'recent.log'
            week_old_file = log_dir / 'week_old.log'
            month_old_file = log_dir / 'month_old.log'
            compressed_file = log_dir / 'compressed.log.gz'
            
            recent_file.write_text('recent content')
            week_old_file.write_text('week old content')
            month_old_file.write_text('month old content')
            compressed_file.write_text('compressed content')
            
            # Set different modification times
            current_time = time.time()
            os.utime(recent_file, (current_time - 3600, current_time - 3600))  # 1 hour ago
            os.utime(week_old_file, (current_time - 7*24*3600, current_time - 7*24*3600))  # 7 days ago
            os.utime(month_old_file, (current_time - 35*24*3600, current_time - 35*24*3600))  # 35 days ago
            os.utime(compressed_file, (current_time - 14*24*3600, current_time - 14*24*3600))  # 14 days ago
            
            # Mock the global config
            with patch('src.logging_config._get_global_config') as mock_config:
                mock_instance = mock_config.return_value
                mock_instance._log_dir = log_dir
                mock_instance._get_log_files.return_value = [recent_file, week_old_file, month_old_file, compressed_file]
                
                # Test get statistics
                stats = get_cleanup_statistics()
                
                # Verify statistics
                assert stats['total_files'] == 4
                assert stats['total_size_mb'] > 0
                assert stats['compressed_files'] == 1
                assert stats['uncompressed_files'] == 3
                assert stats['oldest_file_age_days'] > 30
                assert stats['age_distribution']['0-1_days'] == 1
                assert stats['age_distribution']['1-7_days'] == 0
                assert stats['age_distribution']['7-30_days'] == 2
                assert stats['age_distribution']['30+_days'] == 1
                assert 'log_directory' in stats

    def test_emergency_cleanup(self):
        """Test emergency cleanup functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test files
            active_file = log_dir / 'sonar.log'
            old_file1 = log_dir / 'old1.log'
            old_file2 = log_dir / 'old2.log.gz'
            
            active_file.write_text('active log content')
            old_file1.write_text('old log content 1')
            old_file2.write_text('old compressed content')
            
            # Mock the global config
            with patch('src.logging_config._get_global_config') as mock_config:
                mock_instance = mock_config.return_value
                mock_instance._log_dir = log_dir
                mock_instance._get_log_files.return_value = [active_file, old_file1, old_file2]
                
                # Test emergency cleanup
                result = emergency_cleanup()
                
                # Should remove all files except sonar.log
                assert result['files_removed'] == 2
                assert result['size_freed'] > 0
                assert result['files_kept'] == 1
                assert active_file.exists()
                assert not old_file1.exists()
                assert not old_file2.exists()

    def test_cleanup_with_no_log_directory(self):
        """Test cleanup functions with no log directory."""
        with patch('src.logging_config._get_global_config') as mock_config:
            mock_instance = mock_config.return_value
            mock_instance._log_dir = None
            
            # Test all cleanup functions
            result1 = cleanup_logs_by_age(7)
            result2 = cleanup_logs_by_size(100)
            result3 = compress_all_logs()
            result4 = get_cleanup_statistics()
            result5 = emergency_cleanup()
            
            # All should return error
            assert 'error' in result1
            assert 'error' in result2
            assert 'error' in result3
            assert 'error' in result4
            assert 'error' in result5

    def test_cleanup_with_no_files(self):
        """Test cleanup functions with no files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            with patch('src.logging_config._get_global_config') as mock_config:
                mock_instance = mock_config.return_value
                mock_instance._log_dir = log_dir
                mock_instance._get_log_files.return_value = []
                
                # Test functions with no files
                result1 = cleanup_logs_by_age(7)
                result2 = cleanup_logs_by_size(100)
                result3 = compress_all_logs()
                result4 = get_cleanup_statistics()
                result5 = emergency_cleanup()
                
                # Should handle gracefully
                assert result1['files_removed'] == 0
                assert result2['files_removed'] == 0
                assert result3['files_compressed'] == 0
                assert 'error' in result4
                assert result5['files_removed'] == 0

    def test_cleanup_with_permission_errors(self):
        """Test cleanup functions with permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test file
            test_file = log_dir / 'test.log'
            test_file.write_text('test content')
            
            with patch('src.logging_config._get_global_config') as mock_config:
                mock_instance = mock_config.return_value
                mock_instance._log_dir = log_dir
                mock_instance._get_log_files.return_value = [test_file]
                mock_instance._get_total_size.return_value = 1000  # 1KB
                
                # Mock file operations to raise permission errors
                with patch.object(Path, 'unlink', side_effect=PermissionError("Permission denied")):
                    result1 = cleanup_logs_by_age(0)  # Should try to remove all files
                    result2 = cleanup_logs_by_size(0)  # Should try to remove all files
                    result3 = emergency_cleanup()
                    
                    # Should handle errors gracefully
                    assert result1['files_removed'] == 0
                    assert result2['files_removed'] == 0
                    assert result3['files_removed'] == 0

    def test_compress_all_with_compression_errors(self):
        """Test compress all with compression errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            # Create test file
            test_file = log_dir / 'test.log'
            test_file.write_text('test content')
            
            with patch('src.logging_config._get_global_config') as mock_config:
                mock_instance = mock_config.return_value
                mock_instance._log_dir = log_dir
                mock_instance._get_log_files.return_value = [test_file]
                mock_instance._compress_file.return_value = False  # Compression fails
                
                result = compress_all_logs()
                
                # Should handle compression failures gracefully
                assert result['files_compressed'] == 0
                assert result['total_candidates'] == 1


if __name__ == '__main__':
    unittest.main()