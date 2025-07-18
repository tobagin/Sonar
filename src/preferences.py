"""
Preferences dialog for Sonar application.
"""

import os
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .logging_config import get_logger, set_log_level, get_current_level, add_file_logging, remove_file_logging, configure_retention_policy, get_retention_info, cleanup_logs, cleanup_logs_by_age, cleanup_logs_by_size, compress_all_logs, get_cleanup_statistics, emergency_cleanup  # noqa: E402

logger = get_logger(__name__)


class PreferencesDialog(Adw.PreferencesDialog):
    """Preferences dialog for the Sonar application."""

    def __init__(self, parent: Optional[Gtk.Widget] = None, tunnel_manager=None, ui_update_callback=None) -> None:
        """Initialize the preferences dialog."""
        super().__init__()
        
        # Set transient parent if provided
        if parent:
            # PreferencesDialog doesn't have set_transient_for, but we can set it after creation
            # by calling present() with the parent
            self._parent = parent
        else:
            self._parent = None
        
        # Store tunnel manager reference for refreshing
        self._tunnel_manager = tunnel_manager
        
        # Store UI update callback
        self._ui_update_callback = ui_update_callback
        
        # Create preferences page
        self._create_preferences_page()
        
        # Load current values
        self._load_preferences()
    
    def _create_preferences_page(self) -> None:
        """Create the preferences page."""
        # Create main preferences page
        page = Adw.PreferencesPage()
        page.set_title("General")
        page.set_icon_name("preferences-system-symbolic")
        
        # Tunnel settings group
        tunnel_group = Adw.PreferencesGroup()
        tunnel_group.set_title("Tunnel Settings")
        tunnel_group.set_description("Configure ngrok tunnel settings")
        
        # Ngrok auth token row
        self.auth_token_row = Adw.PasswordEntryRow()
        self.auth_token_row.set_title("Ngrok Auth Token")
        self.auth_token_row.connect("notify::text", self._on_auth_token_changed)
        
        tunnel_group.add(self.auth_token_row)
        
        # Instructions row
        instructions_row = Adw.ActionRow()
        instructions_row.set_title("How to get your ngrok auth token")
        instructions_row.set_subtitle("1. Sign up at ngrok.com\\n2. Go to Auth → Your Authtoken\\n3. Copy the token and paste it above")
        
        # Add open browser button
        open_button = Gtk.Button()
        open_button.set_label("Open ngrok.com")
        open_button.set_valign(Gtk.Align.CENTER)
        open_button.connect("clicked", self._on_open_ngrok_clicked)
        instructions_row.add_suffix(open_button)
        
        tunnel_group.add(instructions_row)
        
        # Add group to page
        page.add(tunnel_group)
        
        # Logging settings group
        logging_group = Adw.PreferencesGroup()
        logging_group.set_title("Logging Settings")
        logging_group.set_description("Configure application logging")
        
        # Log level row
        self.log_level_row = Adw.ComboRow()
        self.log_level_row.set_title("Log Level")
        self.log_level_row.set_subtitle("Set the verbosity of application logs")
        
        # Create log level model
        log_level_model = Gtk.StringList.new(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_row.set_model(log_level_model)
        
        # Set current log level
        current_level = get_current_level()
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if current_level in log_levels:
            self.log_level_row.set_selected(log_levels.index(current_level))
        
        self.log_level_row.connect("notify::selected", self._on_log_level_changed)
        logging_group.add(self.log_level_row)
        
        # File logging switch
        self.file_logging_row = Adw.SwitchRow()
        self.file_logging_row.set_title("Enable File Logging")
        self.file_logging_row.set_subtitle("Save logs to ~/.config/sonar/logs/sonar.log")
        self.file_logging_row.connect("notify::active", self._on_file_logging_changed)
        logging_group.add(self.file_logging_row)
        
        # Log retention days
        self.retention_days_row = Adw.SpinRow()
        self.retention_days_row.set_title("Log Retention Days")
        self.retention_days_row.set_subtitle("Number of days to keep log files")
        self.retention_days_row.set_range(1, 365)
        self.retention_days_row.set_value(30)  # Default value
        self.retention_days_row.connect("notify::value", self._on_retention_days_changed)
        logging_group.add(self.retention_days_row)
        
        # Max total size
        self.max_size_row = Adw.SpinRow()
        self.max_size_row.set_title("Max Total Size (MB)")
        self.max_size_row.set_subtitle("Maximum total size of all log files")
        self.max_size_row.set_range(10, 1000)
        self.max_size_row.set_value(100)  # Default value
        self.max_size_row.connect("notify::value", self._on_max_size_changed)
        logging_group.add(self.max_size_row)
        
        # Cleanup interval
        self.cleanup_interval_row = Adw.SpinRow()
        self.cleanup_interval_row.set_title("Cleanup Interval (Hours)")
        self.cleanup_interval_row.set_subtitle("How often to run log cleanup")
        self.cleanup_interval_row.set_range(1, 168)  # 1 hour to 1 week
        self.cleanup_interval_row.set_value(24)  # Default value
        self.cleanup_interval_row.connect("notify::value", self._on_cleanup_interval_changed)
        logging_group.add(self.cleanup_interval_row)
        
        # Log compression switch
        self.compression_enabled_row = Adw.SwitchRow()
        self.compression_enabled_row.set_title("Enable Log Compression")
        self.compression_enabled_row.set_subtitle("Compress old log files to save disk space")
        self.compression_enabled_row.set_active(True)  # Default enabled
        self.compression_enabled_row.connect("notify::active", self._on_compression_enabled_changed)
        logging_group.add(self.compression_enabled_row)
        
        # Compression age days
        self.compression_age_row = Adw.SpinRow()
        self.compression_age_row.set_title("Compression Age (Days)")
        self.compression_age_row.set_subtitle("Compress files older than this many days")
        self.compression_age_row.set_range(1, 365)
        self.compression_age_row.set_value(7)  # Default value
        self.compression_age_row.connect("notify::value", self._on_compression_age_changed)
        logging_group.add(self.compression_age_row)
        
        # Manual cleanup button
        self.cleanup_button_row = Adw.ActionRow()
        self.cleanup_button_row.set_title("Manual Cleanup")
        self.cleanup_button_row.set_subtitle("Force immediate log cleanup")
        
        cleanup_button = Gtk.Button()
        cleanup_button.set_label("Clean Now")
        cleanup_button.set_valign(Gtk.Align.CENTER)
        cleanup_button.connect("clicked", self._on_cleanup_button_clicked)
        self.cleanup_button_row.add_suffix(cleanup_button)
        logging_group.add(self.cleanup_button_row)
        
        # Advanced cleanup options
        self.advanced_cleanup_row = Adw.ActionRow()
        self.advanced_cleanup_row.set_title("Advanced Cleanup")
        self.advanced_cleanup_row.set_subtitle("Additional cleanup procedures")
        
        # Create a box for multiple buttons
        cleanup_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Compress all button
        compress_button = Gtk.Button()
        compress_button.set_label("Compress All")
        compress_button.set_valign(Gtk.Align.CENTER)
        compress_button.connect("clicked", self._on_compress_all_clicked)
        cleanup_box.append(compress_button)
        
        # Statistics button
        stats_button = Gtk.Button()
        stats_button.set_label("Statistics")
        stats_button.set_valign(Gtk.Align.CENTER)
        stats_button.connect("clicked", self._on_statistics_clicked)
        cleanup_box.append(stats_button)
        
        # Emergency cleanup button
        emergency_button = Gtk.Button()
        emergency_button.set_label("Emergency")
        emergency_button.set_valign(Gtk.Align.CENTER)
        emergency_button.add_css_class("destructive-action")
        emergency_button.connect("clicked", self._on_emergency_cleanup_clicked)
        cleanup_box.append(emergency_button)
        
        self.advanced_cleanup_row.add_suffix(cleanup_box)
        logging_group.add(self.advanced_cleanup_row)
        
        # Add logging group to page
        page.add(logging_group)
        
        # Add page to dialog
        self.add(page)
    
    def _load_preferences(self) -> None:
        """Load current preferences."""
        # Load auth token from environment
        auth_token = os.getenv("NGROK_AUTHTOKEN", "")
        if auth_token:
            self.auth_token_row.set_text(auth_token)
        
        # Load retention policy settings
        try:
            retention_info = get_retention_info()
            if retention_info:
                self.retention_days_row.set_value(retention_info.get('retention_days', 30))
                self.max_size_row.set_value(retention_info.get('max_total_size', 100 * 1024 * 1024) / (1024 * 1024))
                self.cleanup_interval_row.set_value(retention_info.get('cleanup_interval', 24 * 60 * 60) / 3600)
                self.compression_enabled_row.set_active(retention_info.get('compression_enabled', True))
                self.compression_age_row.set_value(retention_info.get('compression_age_days', 7))
        except Exception as e:
            logger.warning(f"Failed to load retention policy settings: {e}")
    
    def _on_auth_token_changed(self, entry: Adw.PasswordEntryRow, param) -> None:
        """Handle auth token change."""
        token = entry.get_text().strip()
        if token:
            # Set environment variable (for current session)
            os.environ["NGROK_AUTHTOKEN"] = token
            logger.info("Ngrok auth token updated")
            
            # Save to config file for persistence
            self._save_to_config_file(token)
            
            # Trigger immediate UI update if callback is available
            if self._ui_update_callback:
                from gi.repository import GLib
                GLib.idle_add(self._ui_update_callback)
            
            logger.info("Ngrok auth token saved")
        else:
            # Remove from environment
            if "NGROK_AUTHTOKEN" in os.environ:
                del os.environ["NGROK_AUTHTOKEN"]
            logger.info("Ngrok auth token removed")
            
            # Remove from config file
            self._remove_from_config_file()
            
            # Trigger immediate UI update if callback is available
            if self._ui_update_callback:
                from gi.repository import GLib
                GLib.idle_add(self._ui_update_callback)
    
    def _save_to_config_file(self, token: str) -> None:
        """Save token to a config file."""
        try:
            # Create .config directory if it doesn't exist
            config_dir = os.path.expanduser("~/.config/sonar")
            os.makedirs(config_dir, exist_ok=True)
            
            # Write token to config file
            config_file = os.path.join(config_dir, "config")
            with open(config_file, "w") as f:
                f.write(f"NGROK_AUTHTOKEN={token}\n")
            
            logger.info(f"Auth token saved to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save auth token to config file: {e}")
    
    def _remove_from_config_file(self) -> None:
        """Remove token from config file."""
        try:
            config_file = os.path.expanduser("~/.config/sonar/config")
            if os.path.exists(config_file):
                os.remove(config_file)
                logger.info(f"Auth token config file removed: {config_file}")
        except Exception as e:
            logger.error(f"Failed to remove auth token config file: {e}")
    
    def _on_open_ngrok_clicked(self, button: Gtk.Button) -> None:
        """Handle open ngrok website button click."""
        try:
            import subprocess
            subprocess.run(["xdg-open", "https://ngrok.com/"], check=False)
        except Exception as e:
            logger.error(f"Failed to open ngrok website: {e}")
    
    def _on_log_level_changed(self, combo_row: Adw.ComboRow, param) -> None:
        """Handle log level change."""
        selected_index = combo_row.get_selected()
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        if 0 <= selected_index < len(log_levels):
            new_level = log_levels[selected_index]
            set_log_level(new_level)
            logger.info(f"Log level changed to {new_level}")
    
    def _on_file_logging_changed(self, switch_row: Adw.SwitchRow, param) -> None:
        """Handle file logging toggle."""
        if switch_row.get_active():
            add_file_logging()
            logger.info("File logging enabled")
        else:
            remove_file_logging()
            logger.info("File logging disabled")
    
    def _on_retention_days_changed(self, spin_row: Adw.SpinRow, param) -> None:
        """Handle retention days change."""
        retention_days = int(spin_row.get_value())
        self._update_retention_policy()
        logger.info(f"Log retention days changed to {retention_days}")
    
    def _on_max_size_changed(self, spin_row: Adw.SpinRow, param) -> None:
        """Handle max size change."""
        max_size_mb = int(spin_row.get_value())
        self._update_retention_policy()
        logger.info(f"Max log size changed to {max_size_mb}MB")
    
    def _on_cleanup_interval_changed(self, spin_row: Adw.SpinRow, param) -> None:
        """Handle cleanup interval change."""
        interval_hours = int(spin_row.get_value())
        self._update_retention_policy()
        logger.info(f"Cleanup interval changed to {interval_hours} hours")
    
    def _on_compression_enabled_changed(self, switch_row: Adw.SwitchRow, param) -> None:
        """Handle compression enabled toggle."""
        compression_enabled = switch_row.get_active()
        self._update_retention_policy()
        logger.info(f"Log compression {'enabled' if compression_enabled else 'disabled'}")
    
    def _on_compression_age_changed(self, spin_row: Adw.SpinRow, param) -> None:
        """Handle compression age change."""
        compression_age = int(spin_row.get_value())
        self._update_retention_policy()
        logger.info(f"Compression age changed to {compression_age} days")
    
    def _update_retention_policy(self) -> None:
        """Update the retention policy with current settings."""
        try:
            retention_days = int(self.retention_days_row.get_value())
            max_size_mb = int(self.max_size_row.get_value())
            interval_hours = int(self.cleanup_interval_row.get_value())
            compression_enabled = self.compression_enabled_row.get_active()
            compression_age = int(self.compression_age_row.get_value())
            
            configure_retention_policy(
                retention_days=retention_days,
                max_total_size=max_size_mb * 1024 * 1024,  # Convert MB to bytes
                cleanup_interval=interval_hours * 3600,    # Convert hours to seconds
                enable_cleanup=True,
                compression_enabled=compression_enabled,
                compression_age_days=compression_age
            )
        except Exception as e:
            logger.error(f"Failed to update retention policy: {e}")
    
    def _on_cleanup_button_clicked(self, button: Gtk.Button) -> None:
        """Handle manual cleanup button click."""
        try:
            button.set_sensitive(False)
            button.set_label("Cleaning...")
            
            # Run cleanup in a separate thread to avoid blocking UI
            def cleanup_task():
                cleanup_logs()
                # Update button text back on main thread
                from gi.repository import GLib
                GLib.idle_add(lambda: self._cleanup_complete(button))
            
            import threading
            cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
            cleanup_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to run manual cleanup: {e}")
            button.set_sensitive(True)
            button.set_label("Clean Now")
    
    def _cleanup_complete(self, button: Gtk.Button) -> None:
        """Handle cleanup completion."""
        button.set_sensitive(True)
        button.set_label("Clean Now")
        logger.info("Manual log cleanup completed")
    
    def _on_compress_all_clicked(self, button: Gtk.Button) -> None:
        """Handle compress all button click."""
        try:
            button.set_sensitive(False)
            button.set_label("Compressing...")
            
            # Run compression in a separate thread
            def compress_task():
                result = compress_all_logs()
                # Update button on main thread
                from gi.repository import GLib
                GLib.idle_add(lambda: self._compress_complete(button, result))
            
            import threading
            compress_thread = threading.Thread(target=compress_task, daemon=True)
            compress_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to compress logs: {e}")
            button.set_sensitive(True)
            button.set_label("Compress All")
    
    def _compress_complete(self, button: Gtk.Button, result: dict) -> None:
        """Handle compress completion."""
        button.set_sensitive(True)
        button.set_label("Compress All")
        
        if 'error' in result:
            logger.error(f"Compression failed: {result['error']}")
        else:
            files_compressed = result.get('files_compressed', 0)
            size_saved = result.get('size_saved', 0)
            logger.info(f"Compression completed: {files_compressed} files compressed, "
                       f"{size_saved / (1024*1024):.1f} MB saved")
    
    def _on_statistics_clicked(self, button: Gtk.Button) -> None:
        """Handle statistics button click."""
        try:
            stats = get_cleanup_statistics()
            
            if 'error' in stats:
                logger.error(f"Statistics error: {stats['error']}")
                return
            
            # Create and show statistics dialog
            dialog = Adw.MessageDialog.new(self, "Log File Statistics", "")
            
            # Format statistics message
            stats_text = f"""Total Files: {stats['total_files']}
Total Size: {stats['total_size_mb']:.1f} MB
Compressed Files: {stats['compressed_files']}
Uncompressed Files: {stats['uncompressed_files']}
Oldest File: {stats['oldest_file_age_days']:.1f} days old
Compression Ratio: {stats['compression_ratio']:.1f}%

Age Distribution:
• 0-1 days: {stats['age_distribution']['0-1_days']} files
• 1-7 days: {stats['age_distribution']['1-7_days']} files
• 7-30 days: {stats['age_distribution']['7-30_days']} files
• 30+ days: {stats['age_distribution']['30+_days']} files

Potential savings if all files compressed: {stats['estimated_savings_if_compressed'] / (1024*1024):.1f} MB"""
            
            dialog.set_body(stats_text)
            dialog.add_response("close", "Close")
            dialog.present()
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
    
    def _on_emergency_cleanup_clicked(self, button: Gtk.Button) -> None:
        """Handle emergency cleanup button click."""
        try:
            # Show confirmation dialog
            dialog = Adw.MessageDialog.new(
                self, 
                "Emergency Cleanup", 
                "This will remove ALL log files except the current one. This action cannot be undone."
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("cleanup", "Emergency Cleanup")
            dialog.set_response_appearance("cleanup", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")
            
            def on_response(dialog, response_id):
                if response_id == "cleanup":
                    self._perform_emergency_cleanup(button)
                dialog.close()
            
            dialog.connect("response", on_response)
            dialog.present()
            
        except Exception as e:
            logger.error(f"Failed to show emergency cleanup dialog: {e}")
    
    def _perform_emergency_cleanup(self, button: Gtk.Button) -> None:
        """Perform emergency cleanup."""
        try:
            button.set_sensitive(False)
            button.set_label("Cleaning...")
            
            # Run emergency cleanup in a separate thread
            def emergency_task():
                result = emergency_cleanup()
                # Update button on main thread
                from gi.repository import GLib
                GLib.idle_add(lambda: self._emergency_complete(button, result))
            
            import threading
            emergency_thread = threading.Thread(target=emergency_task, daemon=True)
            emergency_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to perform emergency cleanup: {e}")
            button.set_sensitive(True)
            button.set_label("Emergency")
    
    def _emergency_complete(self, button: Gtk.Button, result: dict) -> None:
        """Handle emergency cleanup completion."""
        button.set_sensitive(True)
        button.set_label("Emergency")
        
        if 'error' in result:
            logger.error(f"Emergency cleanup failed: {result['error']}")
        else:
            files_removed = result.get('files_removed', 0)
            size_freed = result.get('size_freed', 0)
            logger.info(f"Emergency cleanup completed: {files_removed} files removed, "
                       f"{size_freed / (1024*1024):.1f} MB freed")