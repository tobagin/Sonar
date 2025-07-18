"""
Centralized logging configuration for Sonar.

This module provides a unified logging setup with configurable levels,
formatters, and handlers for consistent logging across the application.
"""

import gzip
import logging
import logging.handlers
import os
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List


class SonarLoggerConfig:
    """Centralized logging configuration for Sonar application."""
    
    # Default log format
    DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
    
    # Log levels mapping
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    def __init__(self):
        """Initialize the logging configuration."""
        self._configured = False
        self._log_dir = None
        self._log_level = logging.INFO
        self._console_handler = None
        self._file_handler = None
        self._detailed_logging = False
        self._is_global_instance = False
        
        # Log retention settings
        self._retention_days = 30  # Default: keep logs for 30 days
        self._max_total_size = 100 * 1024 * 1024  # Default: 100MB total
        self._cleanup_interval = 24 * 60 * 60  # Default: cleanup every 24 hours
        self._cleanup_thread = None
        self._cleanup_enabled = True
        self._last_cleanup = 0
        
        # Log compression settings
        self._compression_enabled = True  # Default: enable compression
        self._compression_age_days = 7  # Default: compress files older than 7 days
        self._compression_format = 'gzip'  # Default: use gzip compression
        
    def configure(
        self,
        log_level: str = 'INFO',
        log_to_file: bool = False,
        log_file_path: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        detailed_logging: bool = False,
        console_logging: bool = True,
        retention_days: int = 30,
        max_total_size: int = 100 * 1024 * 1024,  # 100MB
        cleanup_interval: int = 24 * 60 * 60,  # 24 hours
        enable_cleanup: bool = True,
        compression_enabled: bool = True,
        compression_age_days: int = 7
    ) -> None:
        """
        Configure the centralized logging system.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Whether to log to file
            log_file_path: Path to log file (auto-generated if None)
            max_file_size: Maximum size per log file in bytes
            backup_count: Number of backup files to keep
            detailed_logging: Whether to use detailed format with file/line info
            console_logging: Whether to log to console
            retention_days: Number of days to keep log files
            max_total_size: Maximum total size of all log files in bytes
            cleanup_interval: Interval between cleanup operations in seconds
            enable_cleanup: Whether to enable automatic cleanup
            compression_enabled: Whether to enable log compression
            compression_age_days: Age in days after which to compress log files
        """
        if self._configured:
            return
            
        # Set log level
        self._log_level = self.LOG_LEVELS.get(log_level.upper(), logging.INFO)
        self._detailed_logging = detailed_logging
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self._log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Choose format
        log_format = self.DETAILED_FORMAT if detailed_logging else self.DEFAULT_FORMAT
        formatter = logging.Formatter(log_format)
        
        # Console handler
        if console_logging:
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(self._log_level)
            self._console_handler.setFormatter(formatter)
            root_logger.addHandler(self._console_handler)
        
        # File handler
        if log_to_file:
            log_file = self._get_log_file_path(log_file_path)
            
            # Create log directory if it doesn't exist
            log_file.parent.mkdir(parents=True, exist_ok=True)
            self._log_dir = log_file.parent
            
            # Use rotating file handler
            self._file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            self._file_handler.setLevel(self._log_level)
            self._file_handler.setFormatter(formatter)
            root_logger.addHandler(self._file_handler)
            
            # Log the configuration
            logger = logging.getLogger(__name__)
            logger.info(f"Logging configured - Level: {log_level}, File: {log_file}")
        
        # Configure retention policies
        self._retention_days = retention_days
        self._max_total_size = max_total_size
        self._cleanup_interval = cleanup_interval
        self._cleanup_enabled = enable_cleanup
        
        # Configure compression policies
        self._compression_enabled = compression_enabled
        self._compression_age_days = compression_age_days
        
        # Start cleanup thread if file logging is enabled and cleanup is enabled
        if log_to_file and enable_cleanup:
            self._start_cleanup_thread()
        
        self._configured = True
    
    def _get_log_file_path(self, log_file_path: Optional[str] = None) -> Path:
        """
        Get the log file path.
        
        Args:
            log_file_path: Custom log file path
            
        Returns:
            Path to log file
        """
        if log_file_path:
            return Path(log_file_path)
        
        # Default log directory in user's config directory
        if os.name == 'nt':  # Windows
            log_dir = Path.home() / 'AppData' / 'Local' / 'Sonar' / 'logs'
        else:  # Unix-like systems
            log_dir = Path.home() / '.config' / 'sonar' / 'logs'
        
        self._log_dir = log_dir
        return log_dir / 'sonar.log'
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance with the given name.
        
        Args:
            name: Logger name (typically __name__)
            
        Returns:
            Logger instance
        """
        return logging.getLogger(name)
    
    def set_level(self, level: str) -> None:
        """
        Change the logging level at runtime.
        
        Args:
            level: New logging level
        """
        new_level = self.LOG_LEVELS.get(level.upper(), logging.INFO)
        
        # Update root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(new_level)
        
        # Update handlers
        if self._console_handler:
            self._console_handler.setLevel(new_level)
        if self._file_handler:
            self._file_handler.setLevel(new_level)
        
        self._log_level = new_level
        
        logger = logging.getLogger(__name__)
        logger.info(f"Log level changed to {level}")
    
    def add_file_logging(
        self,
        log_file_path: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,
        backup_count: int = 5
    ) -> None:
        """
        Add file logging to existing configuration.
        
        Args:
            log_file_path: Path to log file
            max_file_size: Maximum size per log file in bytes
            backup_count: Number of backup files to keep
        """
        if self._file_handler:
            return  # Already configured
        
        log_file = self._get_log_file_path(log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Choose format
        log_format = self.DETAILED_FORMAT if self._detailed_logging else self.DEFAULT_FORMAT
        formatter = logging.Formatter(log_format)
        
        # Create and add file handler
        self._file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        self._file_handler.setLevel(self._log_level)
        self._file_handler.setFormatter(formatter)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(self._file_handler)
        
        # Set log directory
        self._log_dir = log_file.parent
        
        logger = logging.getLogger(__name__)
        logger.info(f"File logging added: {log_file}")
    
    def remove_file_logging(self) -> None:
        """Remove file logging from configuration."""
        if not self._file_handler:
            return
        
        root_logger = logging.getLogger()
        root_logger.removeHandler(self._file_handler)
        self._file_handler.close()
        self._file_handler = None
        
        logger = logging.getLogger(__name__)
        logger.info("File logging removed")
    
    def get_log_directory(self) -> Optional[Path]:
        """Get the current log directory."""
        return self._log_dir
    
    def is_configured(self) -> bool:
        """Check if logging is configured."""
        return self._configured
    
    def get_current_level(self) -> str:
        """Get the current log level as string."""
        for name, level in self.LOG_LEVELS.items():
            if level == self._log_level:
                return name
        return 'INFO'
    
    def configure_retention_policy(
        self,
        retention_days: int = 30,
        max_total_size: int = 100 * 1024 * 1024,
        cleanup_interval: int = 24 * 60 * 60,
        enable_cleanup: bool = True,
        compression_enabled: bool = True,
        compression_age_days: int = 7
    ) -> None:
        """
        Configure log retention policies.
        
        Args:
            retention_days: Number of days to keep log files
            max_total_size: Maximum total size of all log files in bytes
            cleanup_interval: Interval between cleanup operations in seconds
            enable_cleanup: Whether to enable automatic cleanup
            compression_enabled: Whether to enable log compression
            compression_age_days: Age in days after which to compress log files
        """
        self._retention_days = retention_days
        self._max_total_size = max_total_size
        self._cleanup_interval = cleanup_interval
        self._cleanup_enabled = enable_cleanup
        self._compression_enabled = compression_enabled
        self._compression_age_days = compression_age_days
        
        # Restart cleanup thread if needed
        if self._cleanup_enabled and self._log_dir:
            self._start_cleanup_thread()
        elif not self._cleanup_enabled:
            self._stop_cleanup_thread()
        
        logger = logging.getLogger(__name__)
        logger.info(f"Retention policy configured - Days: {retention_days}, Max size: {max_total_size}, Cleanup: {enable_cleanup}, Compression: {compression_enabled}")
    
    def _start_cleanup_thread(self) -> None:
        """Start the cleanup thread."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return
        
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        
        logger = logging.getLogger(__name__)
        logger.debug("Log cleanup thread started")
    
    def _stop_cleanup_thread(self) -> None:
        """Stop the cleanup thread."""
        self._cleanup_enabled = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=1.0)
            self._cleanup_thread = None
        
        logger = logging.getLogger(__name__)
        logger.debug("Log cleanup thread stopped")
    
    def _cleanup_worker(self) -> None:
        """Background worker for log cleanup."""
        while self._cleanup_enabled:
            try:
                current_time = time.time()
                
                # Check if it's time for cleanup
                if current_time - self._last_cleanup >= self._cleanup_interval:
                    self.cleanup_logs()
                    self._last_cleanup = current_time
                
                # Sleep for 1 hour between checks
                time.sleep(3600)
                
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error in cleanup worker: {e}")
                time.sleep(3600)  # Sleep and continue
    
    def cleanup_logs(self) -> None:
        """
        Perform log cleanup based on retention policies.
        
        This method performs:
        1. Compression of old log files
        2. Removal of files older than retention period
        3. Removal of files if total size exceeds limit
        """
        if not self._log_dir or not self._log_dir.exists():
            return
        
        logger = logging.getLogger(__name__)
        
        try:
            # Get all log files in the directory
            log_files = self._get_log_files()
            
            if not log_files:
                return
            
            # Sort by modification time (oldest first)
            log_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Step 1: Compress old files if compression is enabled
            files_compressed = 0
            if self._compression_enabled:
                files_compressed = self._compress_old_files(log_files)
                # Refresh log files list after compression
                log_files = self._get_log_files()
                log_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Step 2: Remove files older than retention period
            cutoff_time = time.time() - (self._retention_days * 24 * 60 * 60)
            files_removed_by_age = 0
            
            for log_file in log_files[:]:  # Use slice to avoid modifying list while iterating
                if log_file.stat().st_mtime < cutoff_time:
                    try:
                        log_file.unlink()
                        log_files.remove(log_file)
                        files_removed_by_age += 1
                        logger.debug(f"Removed old log file: {log_file.name}")
                    except Exception as e:
                        logger.warning(f"Failed to remove old log file {log_file.name}: {e}")
            
            # Step 3: Remove files if total size exceeds limit
            files_removed_by_size = 0
            while log_files and self._get_total_size(log_files) > self._max_total_size:
                # Remove oldest file
                oldest_file = log_files.pop(0)
                try:
                    oldest_file.unlink()
                    files_removed_by_size += 1
                    logger.debug(f"Removed log file due to size limit: {oldest_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to remove log file {oldest_file.name}: {e}")
            
            # Log cleanup results
            if files_compressed > 0 or files_removed_by_age > 0 or files_removed_by_size > 0:
                remaining_files = len(log_files)
                total_size = self._get_total_size(log_files)
                logger.info(f"Log cleanup completed - Compressed {files_compressed} files, "
                           f"removed {files_removed_by_age} old files, "
                           f"{files_removed_by_size} files for size limit. "
                           f"Remaining: {remaining_files} files, {total_size / (1024*1024):.1f}MB")
        
        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
    
    def _get_log_files(self) -> List[Path]:
        """Get all log files in the log directory."""
        if not self._log_dir or not self._log_dir.exists():
            return []
        
        log_files = []
        
        # Look for log files with common patterns
        patterns = [
            "*.log",
            "*.log.*",
            "sonar.log*",
            "*.log.gz",
            "*.log.bz2"
        ]
        
        for pattern in patterns:
            log_files.extend(self._log_dir.glob(pattern))
        
        # Remove duplicates and filter out directories
        unique_files = []
        seen = set()
        for file_path in log_files:
            if file_path.is_file() and file_path not in seen:
                unique_files.append(file_path)
                seen.add(file_path)
        
        return unique_files
    
    def _compress_old_files(self, log_files: List[Path]) -> int:
        """
        Compress log files older than compression_age_days.
        
        Args:
            log_files: List of log files to check for compression
            
        Returns:
            Number of files compressed
        """
        if not self._compression_enabled:
            return 0
        
        logger = logging.getLogger(__name__)
        files_compressed = 0
        
        # Calculate compression cutoff time
        compression_cutoff = time.time() - (self._compression_age_days * 24 * 60 * 60)
        
        for log_file in log_files:
            try:
                # Skip already compressed files
                if log_file.suffix in ['.gz', '.bz2', '.xz']:
                    continue
                
                # Skip the current active log file (usually the largest/newest)
                if log_file.name == 'sonar.log':
                    continue
                
                # Check if file is old enough for compression
                if log_file.stat().st_mtime < compression_cutoff:
                    if self._compress_file(log_file):
                        files_compressed += 1
                        logger.debug(f"Compressed log file: {log_file.name}")
            
            except Exception as e:
                logger.warning(f"Failed to compress log file {log_file.name}: {e}")
        
        return files_compressed
    
    def _compress_file(self, log_file: Path) -> bool:
        """
        Compress a single log file using gzip.
        
        Args:
            log_file: Path to the log file to compress
            
        Returns:
            True if compression was successful, False otherwise
        """
        try:
            compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
            
            # Skip if compressed file already exists
            if compressed_file.exists():
                return False
            
            # Read original file and write compressed version
            with open(log_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Preserve modification time
            original_stat = log_file.stat()
            import os
            os.utime(compressed_file, (original_stat.st_atime, original_stat.st_mtime))
            
            # Remove original file
            log_file.unlink()
            
            return True
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to compress {log_file.name}: {e}")
            
            # Clean up partial compressed file if it exists
            compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
            if compressed_file.exists():
                try:
                    compressed_file.unlink()
                except Exception:
                    pass
            
            return False
    
    def decompress_file(self, compressed_file: Path, output_file: Optional[Path] = None) -> bool:
        """
        Decompress a compressed log file.
        
        Args:
            compressed_file: Path to the compressed log file
            output_file: Optional path for the decompressed file
            
        Returns:
            True if decompression was successful, False otherwise
        """
        try:
            if not compressed_file.exists():
                return False
            
            # Determine output file path
            if output_file is None:
                if compressed_file.suffix == '.gz':
                    output_file = compressed_file.with_suffix('')
                else:
                    output_file = compressed_file.with_suffix('.log')
            
            # Skip if output file already exists
            if output_file.exists():
                return False
            
            # Decompress file
            if compressed_file.suffix == '.gz':
                with gzip.open(compressed_file, 'rb') as f_in:
                    with open(output_file, 'wb') as f_out:
                        f_out.writelines(f_in)
            else:
                # Not a compressed file we can handle
                return False
            
            # Preserve modification time
            compressed_stat = compressed_file.stat()
            import os
            os.utime(output_file, (compressed_stat.st_atime, compressed_stat.st_mtime))
            
            return True
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to decompress {compressed_file.name}: {e}")
            
            # Clean up partial decompressed file if it exists
            if output_file and output_file.exists():
                try:
                    output_file.unlink()
                except Exception:
                    pass
            
            return False
    
    def _get_total_size(self, log_files: List[Path]) -> int:
        """Get total size of log files."""
        total_size = 0
        for log_file in log_files:
            try:
                if log_file.exists():
                    total_size += log_file.stat().st_size
            except Exception:
                continue
        return total_size
    
    def get_retention_info(self) -> dict:
        """
        Get information about current retention policies and log files.
        
        Returns:
            Dict with retention policy information and current log file stats
        """
        info = {
            'retention_days': self._retention_days,
            'max_total_size': self._max_total_size,
            'cleanup_interval': self._cleanup_interval,
            'cleanup_enabled': self._cleanup_enabled,
            'compression_enabled': self._compression_enabled,
            'compression_age_days': self._compression_age_days,
            'log_directory': str(self._log_dir) if self._log_dir else None,
            'files': [],
            'total_size': 0,
            'oldest_file_age_days': 0,
            'last_cleanup': datetime.fromtimestamp(self._last_cleanup) if self._last_cleanup else None,
            'compressed_files': 0,
            'uncompressed_files': 0
        }
        
        if self._log_dir and self._log_dir.exists():
            log_files = self._get_log_files()
            
            if log_files:
                # Sort by modification time
                log_files.sort(key=lambda f: f.stat().st_mtime)
                
                # Get file information
                current_time = time.time()
                for log_file in log_files:
                    try:
                        stat = log_file.stat()
                        age_days = (current_time - stat.st_mtime) / (24 * 60 * 60)
                        is_compressed = log_file.suffix in ['.gz', '.bz2', '.xz']
                        
                        info['files'].append({
                            'name': log_file.name,
                            'size': stat.st_size,
                            'age_days': age_days,
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'compressed': is_compressed
                        })
                        
                        # Count compressed vs uncompressed files
                        if is_compressed:
                            info['compressed_files'] += 1
                        else:
                            info['uncompressed_files'] += 1
                            
                    except Exception:
                        continue
                
                info['total_size'] = self._get_total_size(log_files)
                if info['files']:
                    info['oldest_file_age_days'] = max(f['age_days'] for f in info['files'])
        
        return info
    
    def force_cleanup(self) -> None:
        """Force immediate log cleanup."""
        logger = logging.getLogger(__name__)
        logger.info("Forcing log cleanup")
        self.cleanup_logs()
    
    def __del__(self) -> None:
        """Cleanup when object is destroyed."""
        try:
            self._stop_cleanup_thread()
            if self._file_handler:
                self.remove_file_logging()
        except Exception:
            pass  # Ignore errors during cleanup


# Global logger configuration instance
_logger_config = None

def _get_global_config():
    """Get the global logger configuration instance."""
    global _logger_config
    if _logger_config is None:
        _logger_config = SonarLoggerConfig()
    return _logger_config


def configure_logging(
    log_level: str = 'INFO',
    log_to_file: bool = False,
    log_file_path: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    detailed_logging: bool = False,
    console_logging: bool = True,
    retention_days: int = 30,
    max_total_size: int = 100 * 1024 * 1024,
    cleanup_interval: int = 24 * 60 * 60,
    enable_cleanup: bool = True,
    compression_enabled: bool = True,
    compression_age_days: int = 7
) -> None:
    """
    Configure the centralized logging system.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_file_path: Path to log file (auto-generated if None)
        max_file_size: Maximum size per log file in bytes
        backup_count: Number of backup files to keep
        detailed_logging: Whether to use detailed format with file/line info
        console_logging: Whether to log to console
        retention_days: Number of days to keep log files
        max_total_size: Maximum total size of all log files in bytes
        cleanup_interval: Interval between cleanup operations in seconds
        enable_cleanup: Whether to enable automatic cleanup
        compression_enabled: Whether to enable log compression
        compression_age_days: Age in days after which to compress log files
    """
    _get_global_config().configure(
        log_level=log_level,
        log_to_file=log_to_file,
        log_file_path=log_file_path,
        max_file_size=max_file_size,
        backup_count=backup_count,
        detailed_logging=detailed_logging,
        console_logging=console_logging,
        retention_days=retention_days,
        max_total_size=max_total_size,
        cleanup_interval=cleanup_interval,
        enable_cleanup=enable_cleanup,
        compression_enabled=compression_enabled,
        compression_age_days=compression_age_days
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return _get_global_config().get_logger(name)


def set_log_level(level: str) -> None:
    """
    Change the logging level at runtime.
    
    Args:
        level: New logging level
    """
    _get_global_config().set_level(level)


def add_file_logging(
    log_file_path: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> None:
    """
    Add file logging to existing configuration.
    
    Args:
        log_file_path: Path to log file
        max_file_size: Maximum size per log file in bytes
        backup_count: Number of backup files to keep
    """
    _get_global_config().add_file_logging(log_file_path, max_file_size, backup_count)


def remove_file_logging() -> None:
    """Remove file logging from configuration."""
    _get_global_config().remove_file_logging()


def get_log_directory() -> Optional[Path]:
    """Get the current log directory."""
    return _get_global_config().get_log_directory()


def is_configured() -> bool:
    """Check if logging is configured."""
    return _get_global_config().is_configured()


def get_current_level() -> str:
    """Get the current log level as string."""
    return _get_global_config().get_current_level()


def configure_retention_policy(
    retention_days: int = 30,
    max_total_size: int = 100 * 1024 * 1024,
    cleanup_interval: int = 24 * 60 * 60,
    enable_cleanup: bool = True,
    compression_enabled: bool = True,
    compression_age_days: int = 7
) -> None:
    """
    Configure log retention policies.
    
    Args:
        retention_days: Number of days to keep log files
        max_total_size: Maximum total size of all log files in bytes
        cleanup_interval: Interval between cleanup operations in seconds
        enable_cleanup: Whether to enable automatic cleanup
        compression_enabled: Whether to enable log compression
        compression_age_days: Age in days after which to compress log files
    """
    _get_global_config().configure_retention_policy(
        retention_days=retention_days,
        max_total_size=max_total_size,
        cleanup_interval=cleanup_interval,
        enable_cleanup=enable_cleanup,
        compression_enabled=compression_enabled,
        compression_age_days=compression_age_days
    )


def cleanup_logs() -> None:
    """Force immediate log cleanup."""
    _get_global_config().force_cleanup()


def cleanup_logs_by_age(days: int) -> dict:
    """
    Clean up log files older than specified days.
    
    Args:
        days: Number of days - files older than this will be removed
        
    Returns:
        Dict with cleanup results
    """
    config = _get_global_config()
    if not config._log_dir or not config._log_dir.exists():
        return {'files_removed': 0, 'size_freed': 0, 'error': 'No log directory found'}
    
    import time
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    
    log_files = config._get_log_files()
    files_removed = 0
    size_freed = 0
    
    for log_file in log_files:
        try:
            if log_file.stat().st_mtime < cutoff_time:
                file_size = log_file.stat().st_size
                log_file.unlink()
                files_removed += 1
                size_freed += file_size
        except Exception:
            continue
    
    return {
        'files_removed': files_removed,
        'size_freed': size_freed,
        'cutoff_days': days
    }


def cleanup_logs_by_size(max_size_mb: int) -> dict:
    """
    Clean up log files until total size is under the limit.
    
    Args:
        max_size_mb: Maximum total size in MB
        
    Returns:
        Dict with cleanup results
    """
    config = _get_global_config()
    if not config._log_dir or not config._log_dir.exists():
        return {'files_removed': 0, 'size_freed': 0, 'error': 'No log directory found'}
    
    max_size_bytes = max_size_mb * 1024 * 1024
    log_files = config._get_log_files()
    
    # Sort by modification time (oldest first)
    log_files.sort(key=lambda f: f.stat().st_mtime)
    
    files_removed = 0
    size_freed = 0
    
    while log_files and config._get_total_size(log_files) > max_size_bytes:
        oldest_file = log_files.pop(0)
        try:
            file_size = oldest_file.stat().st_size
            oldest_file.unlink()
            files_removed += 1
            size_freed += file_size
        except Exception:
            continue
    
    return {
        'files_removed': files_removed,
        'size_freed': size_freed,
        'max_size_mb': max_size_mb,
        'final_size_mb': config._get_total_size(log_files) / (1024 * 1024)
    }


def compress_all_logs() -> dict:
    """
    Compress all uncompressed log files.
    
    Returns:
        Dict with compression results
    """
    config = _get_global_config()
    if not config._log_dir or not config._log_dir.exists():
        return {'files_compressed': 0, 'size_saved': 0, 'error': 'No log directory found'}
    
    log_files = config._get_log_files()
    
    # Filter for uncompressed files
    uncompressed_files = [f for f in log_files if f.suffix not in ['.gz', '.bz2', '.xz']]
    
    files_compressed = 0
    size_saved = 0
    
    for log_file in uncompressed_files:
        try:
            # Skip active log file
            if log_file.name == 'sonar.log':
                continue
            
            original_size = log_file.stat().st_size
            if config._compress_file(log_file):
                files_compressed += 1
                # Estimate compression savings (gzip typically achieves 60-80% compression)
                size_saved += int(original_size * 0.7)  # Conservative estimate
        except Exception:
            continue
    
    return {
        'files_compressed': files_compressed,
        'size_saved': size_saved,
        'total_candidates': len(uncompressed_files)
    }


def get_cleanup_statistics() -> dict:
    """
    Get detailed statistics about log files for cleanup analysis.
    
    Returns:
        Dict with detailed statistics
    """
    config = _get_global_config()
    if not config._log_dir or not config._log_dir.exists():
        return {'error': 'No log directory found'}
    
    log_files = config._get_log_files()
    if not log_files:
        return {'error': 'No log files found'}
    
    import time
    from datetime import datetime
    
    current_time = time.time()
    total_size = 0
    compressed_size = 0
    uncompressed_size = 0
    compressed_count = 0
    uncompressed_count = 0
    oldest_file_age = 0
    newest_file_age = float('inf')
    
    age_buckets = {
        '0-1_days': 0,
        '1-7_days': 0,
        '7-30_days': 0,
        '30+_days': 0
    }
    
    for log_file in log_files:
        try:
            stat = log_file.stat()
            file_size = stat.st_size
            file_age_days = (current_time - stat.st_mtime) / (24 * 60 * 60)
            
            total_size += file_size
            
            # Track age ranges
            if file_age_days <= 1:
                age_buckets['0-1_days'] += 1
            elif file_age_days <= 7:
                age_buckets['1-7_days'] += 1
            elif file_age_days <= 30:
                age_buckets['7-30_days'] += 1
            else:
                age_buckets['30+_days'] += 1
            
            # Track oldest/newest
            oldest_file_age = max(oldest_file_age, file_age_days)
            newest_file_age = min(newest_file_age, file_age_days)
            
            # Track compression
            if log_file.suffix in ['.gz', '.bz2', '.xz']:
                compressed_count += 1
                compressed_size += file_size
            else:
                uncompressed_count += 1
                uncompressed_size += file_size
                
        except Exception:
            continue
    
    return {
        'total_files': len(log_files),
        'total_size': total_size,
        'total_size_mb': total_size / (1024 * 1024),
        'compressed_files': compressed_count,
        'compressed_size': compressed_size,
        'uncompressed_files': uncompressed_count,
        'uncompressed_size': uncompressed_size,
        'oldest_file_age_days': oldest_file_age,
        'newest_file_age_days': newest_file_age if newest_file_age != float('inf') else 0,
        'age_distribution': age_buckets,
        'compression_ratio': (compressed_size / total_size * 100) if total_size > 0 else 0,
        'estimated_savings_if_compressed': int(uncompressed_size * 0.7),  # Conservative estimate
        'log_directory': str(config._log_dir)
    }


def emergency_cleanup() -> dict:
    """
    Emergency cleanup procedure - removes all log files except the current one.
    
    Returns:
        Dict with cleanup results
    """
    config = _get_global_config()
    if not config._log_dir or not config._log_dir.exists():
        return {'files_removed': 0, 'size_freed': 0, 'error': 'No log directory found'}
    
    log_files = config._get_log_files()
    files_removed = 0
    size_freed = 0
    
    for log_file in log_files:
        try:
            # Keep the current active log file
            if log_file.name == 'sonar.log':
                continue
            
            file_size = log_file.stat().st_size
            log_file.unlink()
            files_removed += 1
            size_freed += file_size
        except Exception:
            continue
    
    return {
        'files_removed': files_removed,
        'size_freed': size_freed,
        'files_kept': 1 if (config._log_dir / 'sonar.log').exists() else 0
    }


def get_retention_info() -> dict:
    """
    Get information about current retention policies and log files.
    
    Returns:
        Dict with retention policy information and current log file stats
    """
    return _get_global_config().get_retention_info()


def decompress_log_file(compressed_file: str, output_file: Optional[str] = None) -> bool:
    """
    Decompress a compressed log file.
    
    Args:
        compressed_file: Path to the compressed log file
        output_file: Optional path for the decompressed file
        
    Returns:
        True if decompression was successful, False otherwise
    """
    from pathlib import Path
    return _get_global_config().decompress_file(Path(compressed_file), Path(output_file) if output_file else None)


def reset_logging() -> None:
    """Reset logging configuration (for testing)."""
    global _logger_config
    if _logger_config:
        _logger_config._stop_cleanup_thread()
        _logger_config.remove_file_logging()
        # Reset root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.WARNING)
    _logger_config = None