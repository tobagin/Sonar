"""
Preferences dialog for Echo application.
"""

import logging
import os
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

logger = logging.getLogger(__name__)


class PreferencesDialog(Adw.PreferencesDialog):
    """Preferences dialog for the Echo application."""

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
        
        # Add page to dialog
        self.add(page)
    
    def _load_preferences(self) -> None:
        """Load current preferences."""
        # Load auth token from environment
        auth_token = os.getenv("NGROK_AUTHTOKEN", "")
        if auth_token:
            self.auth_token_row.set_text(auth_token)
    
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
            config_dir = os.path.expanduser("~/.config/echo")
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
            config_file = os.path.expanduser("~/.config/echo/config")
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