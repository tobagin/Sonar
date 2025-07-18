# Log Cleanup Procedures for Sonar

This document outlines the cleanup procedures for Sonar log files in a Flatpak environment.

## Overview

Sonar includes built-in automatic log cleanup functionality that handles:
- **Age-based retention**: Removes log files older than configured days
- **Size-based retention**: Removes oldest files when total size exceeds limit
- **Compression**: Compresses old log files to save space
- **Background cleanup**: Runs automatically at configured intervals

## Automatic Cleanup

The application automatically manages log cleanup through:

1. **Background Thread**: Runs cleanup at configured intervals (default: 24 hours)
2. **Retention Policies**: Configurable through the preferences dialog
3. **Compression**: Automatically compresses files older than 7 days (configurable)

### Default Settings

- **Retention Days**: 30 days
- **Max Total Size**: 100 MB
- **Cleanup Interval**: 24 hours
- **Compression**: Enabled for files older than 7 days

## Manual Cleanup Procedures

### 1. Through the Application UI

1. Open Sonar
2. Go to **Preferences** → **Logging Settings**
3. Click **"Clean Now"** button for immediate cleanup
4. Adjust retention settings as needed

### 2. Manual File Cleanup

Since Sonar is a Flatpak application, log files are stored in:
```
~/.var/app/io.github.tobagin.sonar/config/sonar/logs/
```

#### View Current Logs
```bash
ls -la ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/
```

#### Check Log Directory Size
```bash
du -sh ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/
```

#### Manual Cleanup Commands

**Remove logs older than 30 days:**
```bash
find ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/ -name "*.log*" -mtime +30 -delete
```

**Remove all log files (use with caution):**
```bash
rm -f ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/*.log*
```

**Compress old log files manually:**
```bash
find ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/ -name "*.log" -mtime +7 -exec gzip {} \;
```

### 3. Flatpak Data Management

#### Complete Application Data Reset
```bash
# Remove all Sonar data (logs, settings, cache)
flatpak uninstall --delete-data io.github.tobagin.sonar
```

#### View Flatpak Application Data
```bash
# Show data directory
ls -la ~/.var/app/io.github.tobagin.sonar/

# Show data usage
du -sh ~/.var/app/io.github.tobagin.sonar/
```

## Cleanup Scheduling

### Using Systemd User Services (Optional)

For automated cleanup outside the application, create a user service:

1. **Create the service file:**
```bash
mkdir -p ~/.config/systemd/user
```

2. **Create `~/.config/systemd/user/sonar-cleanup.service`:**
```ini
[Unit]
Description=Sonar Log Cleanup
Documentation=https://github.com/tobagin/sonar

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'find ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/ -name "*.log*" -mtime +30 -delete'
StandardOutput=journal
StandardError=journal
```

3. **Create `~/.config/systemd/user/sonar-cleanup.timer`:**
```ini
[Unit]
Description=Run Sonar Log Cleanup Daily
Requires=sonar-cleanup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

4. **Enable and start the timer:**
```bash
systemctl --user enable sonar-cleanup.timer
systemctl --user start sonar-cleanup.timer
```

### Using Cron (Alternative)

Add to user crontab (`crontab -e`):
```bash
# Clean Sonar logs daily at 2 AM
0 2 * * * find ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/ -name "*.log*" -mtime +30 -delete
```

## Log File Patterns

Sonar creates the following log files:
- `sonar.log` - Current log file
- `sonar.log.1`, `sonar.log.2`, etc. - Rotated log files
- `*.log.gz` - Compressed log files

## Monitoring and Maintenance

### Check Cleanup Status

The application logs cleanup activities. Look for entries like:
```
INFO - Log cleanup completed - Compressed 3 files, removed 2 old files, 1 files for size limit
```

### Verify Cleanup Operation

After cleanup, verify the results:
```bash
# Check remaining log files
ls -la ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/

# Check total size
du -sh ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/

# Check oldest file
find ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/ -name "*.log*" -printf '%T@ %p\n' | sort -n | head -1
```

## Troubleshooting

### Cleanup Not Working

1. **Check if cleanup is enabled:**
   - Open Preferences → Logging Settings
   - Verify "Cleanup Interval" is set
   - Ensure retention days and max size are reasonable

2. **Check application logs:**
   - Look for cleanup-related messages
   - Check for permission errors

3. **Manual cleanup test:**
   - Use the "Clean Now" button
   - Check if files are actually removed

### Disk Space Issues

If logs are consuming too much space:

1. **Immediate action:**
   ```bash
   # Remove all logs (emergency)
   rm -f ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/*.log*
   ```

2. **Adjust settings:**
   - Reduce retention days
   - Reduce max total size
   - Enable compression if disabled

### Permission Issues

If cleanup fails due to permissions:
```bash
# Fix permissions
chmod -R u+w ~/.var/app/io.github.tobagin.sonar/config/sonar/logs/
```

## Best Practices

1. **Monitor regularly**: Check log directory size occasionally
2. **Adjust retention**: Set appropriate retention based on your needs
3. **Enable compression**: Keeps more history while using less space
4. **Test cleanup**: Verify cleanup is working as expected
5. **Backup important logs**: Archive critical logs before cleanup if needed

## Configuration Recommendations

### For Development
- Retention: 7 days
- Max size: 50 MB
- Compression: 3 days
- Cleanup interval: 12 hours

### For Production
- Retention: 30 days
- Max size: 100 MB
- Compression: 7 days
- Cleanup interval: 24 hours

### For Limited Storage
- Retention: 7 days
- Max size: 25 MB
- Compression: 1 day
- Cleanup interval: 6 hours

## Integration with Application

The cleanup procedures integrate with the application's logging system:

1. **Automatic background cleanup** runs according to configured schedule
2. **Manual cleanup** available through preferences dialog
3. **Compression** happens automatically based on file age
4. **Retention policies** are enforced during cleanup
5. **Statistics** are tracked and reported

This ensures that log management is seamless and doesn't require manual intervention under normal circumstances.