# Centralized Logging System

Sonar uses a centralized logging system built on Python's `logging` module that provides consistent, configurable logging across the entire application.

## Features

- **Centralized Configuration**: Single point of configuration for all logging
- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **File Logging**: Optional file logging with automatic rotation
- **Console Logging**: Configurable console output
- **Detailed Logging**: Optional detailed format with file/line information
- **Runtime Configuration**: Change log levels and settings at runtime
- **User Interface**: Preferences dialog for logging configuration

## Quick Start

### Basic Usage

```python
from src.logging_config import configure_logging, get_logger

# Configure logging (typically done once at application startup)
configure_logging(
    log_level='INFO',
    console_logging=True,
    log_to_file=False
)

# Get a logger instance
logger = get_logger(__name__)

# Use the logger
logger.info("Application started")
logger.warning("This is a warning")
logger.error("An error occurred")
```

### File Logging

```python
from src.logging_config import configure_logging, get_logger

# Enable file logging
configure_logging(
    log_level='DEBUG',
    log_to_file=True,
    log_file_path='/path/to/logfile.log',  # Optional, auto-generated if not provided
    max_file_size=10 * 1024 * 1024,  # 10MB
    backup_count=5,
    detailed_logging=True
)

logger = get_logger(__name__)
logger.debug("Debug message with detailed format")
```

### Runtime Configuration

```python
from src.logging_config import set_log_level, add_file_logging, remove_file_logging

# Change log level at runtime
set_log_level('DEBUG')

# Add file logging to existing configuration
add_file_logging('/path/to/logfile.log')

# Remove file logging
remove_file_logging()
```

### Log Retention Policies

```python
from src.logging_config import configure_retention_policy, cleanup_logs, get_retention_info

# Configure retention policies
configure_retention_policy(
    retention_days=14,          # Keep logs for 14 days
    max_total_size=50 * 1024 * 1024,  # Max 50MB total
    cleanup_interval=12 * 3600,       # Cleanup every 12 hours
    enable_cleanup=True,
    compression_enabled=True,          # Enable compression
    compression_age_days=7             # Compress files older than 7 days
)

# Force immediate cleanup
cleanup_logs()

# Get retention information
info = get_retention_info()
print(f"Retention: {info['retention_days']} days")
print(f"Total size: {info['total_size']} bytes")
print(f"Files: {len(info['files'])}")
print(f"Compressed files: {info['compressed_files']}")
print(f"Uncompressed files: {info['uncompressed_files']}")
```

### Log Compression

```python
from src.logging_config import decompress_log_file

# Decompress a compressed log file
success = decompress_log_file('/path/to/compressed.log.gz')
if success:
    print("Log file decompressed successfully")

# Decompress with custom output path
success = decompress_log_file('/path/to/compressed.log.gz', '/path/to/output.log')
```

## Configuration Options

### Log Levels

- **DEBUG**: Detailed information, typically only of interest when diagnosing problems
- **INFO**: General information about program execution
- **WARNING**: An indication that something unexpected happened
- **ERROR**: A serious problem occurred
- **CRITICAL**: A very serious error occurred

### File Logging Options

- **log_file_path**: Path to log file (auto-generated if not provided)
- **max_file_size**: Maximum size per log file in bytes (default: 10MB)
- **backup_count**: Number of backup files to keep (default: 5)
- **detailed_logging**: Include file/line information in log messages

### Log Retention Policies

- **retention_days**: Number of days to keep log files (default: 30)
- **max_total_size**: Maximum total size of all log files in bytes (default: 100MB)
- **cleanup_interval**: Interval between cleanup operations in seconds (default: 24 hours)
- **enable_cleanup**: Whether to enable automatic cleanup (default: True)
- **compression_enabled**: Whether to enable log compression (default: True)
- **compression_age_days**: Age in days after which to compress log files (default: 7)

### Default Log Locations

- **Linux/macOS**: `~/.config/sonar/logs/sonar.log`
- **Windows**: `%LOCALAPPDATA%/Sonar/logs/sonar.log`

## Log Formats

### Standard Format
```
2025-01-01 12:00:00,123 - module.name - INFO - Log message
```

### Detailed Format
```
2025-01-01 12:00:00,123 - module.name - INFO - filename.py:42 - function_name - Log message
```

## User Interface

Users can configure logging through the Preferences dialog:

1. **Log Level**: Choose from DEBUG, INFO, WARNING, ERROR, CRITICAL
2. **Enable File Logging**: Toggle file logging on/off
3. **Log Retention Days**: Number of days to keep log files (1-365)
4. **Max Total Size**: Maximum total size of all log files in MB (10-1000)
5. **Cleanup Interval**: How often to run cleanup in hours (1-168)
6. **Enable Log Compression**: Toggle compression for old log files
7. **Compression Age**: Age in days after which to compress files (1-365)
8. **Manual Cleanup**: Force immediate log cleanup with "Clean Now" button
9. **Log Location**: Files are saved to `~/.config/sonar/logs/sonar.log`

## Best Practices

### Logger Creation

Always create loggers using the centralized system:

```python
from src.logging_config import get_logger

logger = get_logger(__name__)  # Use __name__ for module-specific loggers
```

### Log Messages

- Use appropriate log levels
- Include context in log messages
- Use structured logging for complex data
- Avoid logging sensitive information

```python
# Good
logger.info(f"Processing request {request_id} from {client_ip}")
logger.warning(f"Rate limit exceeded for user {user_id}: {attempt_count} attempts")

# Avoid
logger.info("Processing request")
logger.error("Error occurred")
```

### Error Logging

```python
try:
    # Some operation
    result = risky_operation()
    logger.info(f"Operation completed successfully: {result}")
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)  # Include stack trace
```

## Testing

The logging system includes comprehensive tests and a reset function for testing:

```python
from src.logging_config import reset_logging

def setUp(self):
    reset_logging()  # Reset logging configuration before each test
```

## Architecture

### Components

1. **SonarLoggerConfig**: Main configuration class
2. **Global Functions**: Convenient API for common operations
3. **Handler Management**: Automatic handler creation and management
4. **Log Rotation**: Automatic file rotation based on size
5. **Retention Policies**: Automatic cleanup based on age and size
6. **Log Compression**: Automatic compression of old log files using gzip
7. **Background Cleanup**: Daemon thread for automatic maintenance

### Thread Safety

The logging system is thread-safe and can be used safely across multiple threads. The cleanup thread runs as a daemon and uses proper locking.

### Memory Management

- Automatic cleanup of handlers
- Proper resource management for file handlers
- No memory leaks from logger instances
- Background cleanup thread with proper lifecycle management

## Troubleshooting

### Common Issues

1. **No log output**: Check if logging is configured and log level is appropriate
2. **File logging not working**: Verify permissions and disk space
3. **Log rotation issues**: Check file permissions and backup count settings

### Debug Configuration

```python
# Enable debug logging to see logging system operations
configure_logging(log_level='DEBUG', detailed_logging=True)
```

## Migration from Basic Logging

If you're migrating from basic logging, replace:

```python
# Old
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# New
from src.logging_config import configure_logging, get_logger
configure_logging(log_level='INFO')
logger = get_logger(__name__)
```

## Performance Considerations

- Logging calls are fast when the log level is disabled
- File logging adds minimal overhead
- Log rotation is handled automatically
- Memory usage is minimal and stable