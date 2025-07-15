"""
Main application module for Sonar.
"""

import logging
import sys
import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# GTK imports must come after gi.require_version
from gi.repository import Adw, Gio, Gtk  # noqa: E402

# Load resources immediately before any other imports
def _load_resources():
    """Load application resources using karere-style multi-path approach."""
    # Multiple potential resource paths
    resource_paths = [
        '/app/lib/python3.12/site-packages/sonar-resources.gresource',
        '/app/share/sonar/sonar-resources.gresource',
        '/usr/share/sonar/sonar-resources.gresource',
        os.path.join(os.path.dirname(__file__), '..', '..', 'builddir', 'data', 'sonar-resources.gresource'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sonar-resources.gresource'),
        'data/sonar-resources.gresource'  # Development fallback
    ]
    
    for resource_path in resource_paths:
        if os.path.exists(resource_path):
            try:
                resource = Gio.Resource.load(resource_path)
                Gio.resources_register(resource)
                return True
            except Exception as e:
                continue
    
    # Resources not found, but don't print error as it's handled in the app
    return False

# Load resources immediately
_load_resources()

from .main_window import SonarWindow  # noqa: E402
from .models import RequestStorage  # noqa: E402
from .preferences import PreferencesDialog  # noqa: E402
from .server import WebhookServer  # noqa: E402
from .tunnel import TunnelManager  # noqa: E402

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SonarApplication(Adw.Application):
    """The main Sonar application."""

    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__(
            application_id="io.github.tobagin.sonar",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )



        # Core components
        self.storage = RequestStorage()
        self.server = WebhookServer(self.storage)
        self.tunnel_manager = TunnelManager()

        # Window reference
        self.window: SonarWindow | None = None

        # Connect signals
        self.connect("activate", self.on_activate)
        self.connect("shutdown", self.on_shutdown)

        # Set up actions
        self._setup_actions()

    def _setup_actions(self) -> None:
        """Set up application actions."""

        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit_action)
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<primary>q"])

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.add_action(about_action)

        # Preferences action
        preferences_action = Gio.SimpleAction.new("preferences", None)
        preferences_action.connect("activate", self.on_preferences_action)
        self.add_action(preferences_action)
        self.set_accels_for_action("app.preferences", ["<primary>comma"])


        # Clear requests action
        clear_requests_action = Gio.SimpleAction.new("clear-requests", None)
        clear_requests_action.connect("activate", self.on_clear_requests_action)
        self.add_action(clear_requests_action)
        self.set_accels_for_action("app.clear-requests", ["<primary>l"])

        # Copy URL action
        copy_url_action = Gio.SimpleAction.new("copy-url", None)
        copy_url_action.connect("activate", self.on_copy_url_action)
        self.add_action(copy_url_action)
        self.set_accels_for_action("app.copy-url", ["<primary>u"])

        # Toggle tunnel action (start/stop)
        toggle_tunnel_action = Gio.SimpleAction.new("toggle-tunnel", None)
        toggle_tunnel_action.connect("activate", self.on_toggle_tunnel_action)
        self.add_action(toggle_tunnel_action)
        self.set_accels_for_action("app.toggle-tunnel", ["<primary>t"])

        # Refresh action
        refresh_action = Gio.SimpleAction.new("refresh", None)
        refresh_action.connect("activate", self.on_refresh_action)
        self.add_action(refresh_action)
        self.set_accels_for_action("app.refresh", ["F5"])

        # Toggle fullscreen action
        fullscreen_action = Gio.SimpleAction.new("toggle-fullscreen", None)
        fullscreen_action.connect("activate", self.on_toggle_fullscreen_action)
        self.add_action(fullscreen_action)
        self.set_accels_for_action("app.toggle-fullscreen", ["F11"])

        # Copy request data action (context-sensitive)
        copy_request_action = Gio.SimpleAction.new("copy-request", None)
        copy_request_action.connect("activate", self.on_copy_request_action)
        self.add_action(copy_request_action)
        self.set_accels_for_action("app.copy-request", ["<primary>c"])

        # View history action
        view_history_action = Gio.SimpleAction.new("view-history", None)
        view_history_action.connect("activate", self.on_view_history_action)
        self.add_action(view_history_action)
        self.set_accels_for_action("app.view-history", ["<primary>h"])

    def on_activate(self, app: Adw.Application) -> None:
        """Handle application activation."""
        if not self.window:
            self.window = SonarWindow(
                application=app,
                storage=self.storage,
                server=self.server,
                tunnel_manager=self.tunnel_manager
            )

        self.window.present()

    def on_shutdown(self, app: Adw.Application) -> None:
        """Handle application shutdown."""
        logger.info("Shutting down application...")

        # Save any active requests to history before shutdown
        if self.window and hasattr(self.window, 'request_rows') and self.window.request_rows:
            try:
                logger.info(f"Moving {len(self.window.request_rows)} active requests to history before shutdown")
                self.storage.clear()  # This moves active requests to history
                logger.info("Successfully moved active requests to history during shutdown")
            except Exception as e:
                logger.error(f"Error saving requests to history during shutdown: {e}")

        # Stop server and tunnel
        try:
            self.server.stop()
            self.tunnel_manager.stop()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
    def on_quit_action(self, action: Gio.SimpleAction, param: None) -> None:
        """Handle quit action."""
        self.quit()

    def on_about_action(self, action: Gio.SimpleAction, param: None) -> None:
        """Handle about action."""
        about = Adw.AboutDialog(
            application_name="Sonar",
            application_icon="io.github.tobagin.sonar",
            developer_name="Thiago Fernandes",
            version="1.0.3",
            developers=["Thiago Fernandes https://github.com/tobagin"],
            copyright="© 2025 Thiago Fernandes",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/tobagin/sonar",
            support_url="https://github.com/tobagin/sonar/discussions",
            issue_url="https://github.com/tobagin/sonar/issues",
            comments="Desktop developer utility for capturing and inspecting webhook requests",
            # Add more detailed information
            translator_credits="""Thiago Fernandes""",
            # Additional links that will appear in the Details section
        )
        
        # Present dialog with transient parent
        
        # Add additional links that appear in the Details section
        about.add_link("Report Issues", "https://github.com/tobagin/sonar/issues")
        about.add_link("Discussions", "https://github.com/tobagin/sonar/discussions")
        about.add_link("Releases", "https://github.com/tobagin/sonar/releases")
        
        # Add credit for technologies used
        about.add_credit_section("Built With", [
            "GTK4 & Libadwaita",
            "Python & FastAPI", 
            "Ngrok",
            "Meson & Flatpak"
        ])
        
        # Add acknowledgments
        about.add_acknowledgement_section("Special Thanks", [
            "GNOME Project for GTK4 & Libadwaita",
            "Ngrok team for tunnel infrastructure",
            "Flatpak community for packaging tools"
        ])
        
        about.present(self.window)

    def on_preferences_action(self, action: Gio.SimpleAction, param: None) -> None:
        """Handle preferences action."""
        preferences = PreferencesDialog(
            parent=self.window, 
            tunnel_manager=self.tunnel_manager,
            ui_update_callback=self.window._update_ui_state if self.window else None
        )
        preferences.present(self.window)
        
        # Connect to dialog close event to refresh UI
        if self.window:
            preferences.connect("closed", self.window._on_preferences_closed)


    def on_clear_requests_action(self, action: Gio.SimpleAction, param: None) -> None:
        """Handle clear requests action."""
        if self.window:
            self.window.clear_requests()

    def on_copy_url_action(self, action: Gio.SimpleAction, param: None) -> None:
        """Handle copy URL action."""
        if self.window:
            self.window.copy_tunnel_url()

    def on_toggle_tunnel_action(self, action: Gio.SimpleAction, param: None) -> None:
        """Handle toggle tunnel action."""
        if self.window:
            self.window.toggle_tunnel()

    def on_refresh_action(self, action: Gio.SimpleAction, param: None) -> None:
        """Handle refresh action."""
        if self.window:
            self.window.refresh_ui()

    def on_toggle_fullscreen_action(self, action: Gio.SimpleAction, param: None) -> None:
        """Handle toggle fullscreen action."""
        if self.window:
            self.window.toggle_fullscreen()

    def on_copy_request_action(self, action: Gio.SimpleAction, param: None) -> None:
        """Handle copy request data action."""
        if self.window:
            self.window.copy_focused_request()

    def on_view_history_action(self, action: Gio.SimpleAction, param: None) -> None:
        """Handle view history action."""
        if self.window:
            self.window._on_history_button_clicked(None)


def main() -> int:
    """Main entry point."""
    try:
        app = SonarApplication()
        exit_code = app.run(sys.argv)
        return exit_code
    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
