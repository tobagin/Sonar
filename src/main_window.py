"""
Main window implementation for Sonar.
"""

import logging
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# GTK imports must come after gi.require_version
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from .models import RequestStorage, TunnelStatus, WebhookRequest  # noqa: E402
from .request_row import RequestRow  # noqa: E402
from .server import WebhookServer  # noqa: E402
from .tunnel import TunnelManager  # noqa: E402
from .error_handler import process_error, ErrorCategory  # noqa: E402
from .error_dialog import show_error_dialog, show_error_toast  # noqa: E402

logger = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/tobagin/sonar/ui/main_window.ui")
class SonarWindow(Adw.ApplicationWindow):
    """Main window for the Sonar application."""

    __gtype_name__ = "SonarWindow"

    # Template children
    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    header_bar: Adw.HeaderBar = Gtk.Template.Child()
    header_stop_button: Gtk.Button = Gtk.Template.Child()
    header_history_button: Gtk.Button = Gtk.Template.Child()
    status_banner: Adw.Banner = Gtk.Template.Child()
    main_stack: Gtk.Stack = Gtk.Template.Child()
    empty_page: Adw.StatusPage = Gtk.Template.Child()
    url_label: Gtk.Label = Gtk.Template.Child()
    tunnel_controls: Gtk.Box = Gtk.Template.Child()
    setup_token_button: Gtk.Button = Gtk.Template.Child()
    start_tunnel_container: Gtk.Box = Gtk.Template.Child()
    start_tunnel_button: Gtk.Button = Gtk.Template.Child()
    tunnel_spinner: Gtk.Spinner = Gtk.Template.Child()
    copy_url_button: Gtk.Button = Gtk.Template.Child()
    stop_tunnel_button: Gtk.Button = Gtk.Template.Child()
    request_list: Gtk.ListBox = Gtk.Template.Child()
    clear_container: Gtk.Box = Gtk.Template.Child()
    history_button: Gtk.Button = Gtk.Template.Child()
    clear_button: Gtk.Button = Gtk.Template.Child()
    clear_spinner: Gtk.Spinner = Gtk.Template.Child()
    history_list: Gtk.ListBox = Gtk.Template.Child()
    history_controls: Gtk.Box = Gtk.Template.Child()
    history_stats_button: Gtk.Button = Gtk.Template.Child()
    export_history_button: Gtk.Button = Gtk.Template.Child()
    back_to_requests_button: Gtk.Button = Gtk.Template.Child()
    clear_history_button: Gtk.Button = Gtk.Template.Child()
    history_search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    history_method_filter: Gtk.DropDown = Gtk.Template.Child()

    def __init__(
        self,
        application: Adw.Application,
        storage: RequestStorage,
        server: WebhookServer,
        tunnel_manager: TunnelManager,
        **kwargs
    ) -> None:
        """Initialize the main window."""
        super().__init__(application=application, **kwargs)

        # Store references
        self.application = application
        self.storage = storage
        self.server = server
        self.tunnel_manager = tunnel_manager

        # State
        self.tunnel_active = False
        self.server_port = 8000
        self.has_received_webhooks = False
        self.request_rows = []  # Track all request rows for accordion behavior
        self.history_rows = []  # Track all history rows for accordion behavior
        self.filtered_history_rows = []  # Track filtered history rows
        self._tunnel_loading = False  # Track tunnel operation state
        self._clear_loading = False  # Track clear operation state
        self._current_search_query = ""  # Current search query
        self._current_method_filter = None  # Current method filter

        # Set up UI
        self._setup_ui()
        self._setup_signals()

        # Set up server callback
        self.server.set_request_callback(self._on_request_received)

        # Check initial state
        self._update_ui_state()

    def _show_toast(self, message: str, timeout: int = 3) -> None:
        """Show a toast notification with the given message.
        
        Args:
            message (str): The message to display in the toast.
            timeout (int): How long to show the toast in seconds (default: 3).
        """
        toast = Adw.Toast(title=message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)

    def _set_tunnel_loading(self, loading: bool) -> None:
        """Set the tunnel loading state and update UI accordingly.
        
        Args:
            loading (bool): Whether tunnel operation is in progress.
        """
        self._tunnel_loading = loading
        self.tunnel_spinner.set_visible(loading)
        self.tunnel_spinner.set_spinning(loading)
        
        # Disable start button during loading
        self.start_tunnel_button.set_sensitive(not loading)
        
        # Update button text based on loading state
        if loading:
            self.start_tunnel_button.set_label("Starting...")
        else:
            self.start_tunnel_button.set_label("Start Tunnel")
        

    def _set_clear_loading(self, loading: bool) -> None:
        """Set the clear operation loading state and update UI accordingly.
        
        Args:
            loading (bool): Whether clear operation is in progress.
        """
        self._clear_loading = loading
        self.clear_spinner.set_visible(loading)
        self.clear_spinner.set_spinning(loading)
        
        # Disable clear button during loading
        self.clear_button.set_sensitive(not loading)
        

    def _setup_ui(self) -> None:
        """Set up the UI elements."""
        # Configure the list box
        self.request_list.set_placeholder(
            Gtk.Label(label="No requests received yet", margin_top=50, margin_bottom=50)
        )

        # Set up banner - ensure it's hidden initially
        self.status_banner.set_revealed(False)
        
        # Set up banner button connection
        self.status_banner.connect("button-clicked", self._on_copy_url_clicked)
        
        # Header stop button is hidden initially
        self.header_stop_button.set_visible(False)

        # Set up URL label
        self.url_label.set_text("Click 'Start Tunnel' to begin receiving webhooks")

        # Configure history list
        self.history_list.set_placeholder(
            Gtk.Label(label="No requests in history", margin_top=50, margin_bottom=50)
        )
        
        # Set up method filter dropdown
        self._setup_method_filter()

        # Initialize history button visibility
        self._update_history_button_visibility()

        # Initial stack page
        self.main_stack.set_visible_child_name("empty")

    def _setup_signals(self) -> None:
        """Set up signal connections."""
        # Button signals
        self.setup_token_button.connect("clicked", self._on_setup_token_clicked)
        self.start_tunnel_button.connect("clicked", self._on_start_tunnel_clicked)
        self.copy_url_button.connect("clicked", self._on_copy_url_clicked)
        self.stop_tunnel_button.connect("clicked", self._on_stop_tunnel_clicked)
        self.header_stop_button.connect("clicked", self._on_stop_tunnel_clicked)
        self.header_history_button.connect("clicked", self._on_history_button_clicked)
        self.history_button.connect("clicked", self._on_history_button_clicked)
        self.clear_button.connect("clicked", self._on_clear_button_clicked)
        self.history_stats_button.connect("clicked", self._on_history_stats_clicked)
        self.export_history_button.connect("clicked", self._on_export_history_clicked)
        self.back_to_requests_button.connect("clicked", self._on_back_to_requests_clicked)
        self.clear_history_button.connect("clicked", self._on_clear_history_clicked)
        
        # History search and filter signals
        self.history_search_entry.connect("search-changed", self._on_search_changed)
        self.history_method_filter.connect("notify::selected", self._on_method_filter_changed)

        # Window signals
        self.connect("close-request", self._on_close_request)

    def _on_setup_token_clicked(self, button: Gtk.Button) -> None:
        """Handle setup token button click."""
        self._show_token_setup_dialog()
    
    def _on_start_tunnel_clicked(self, button: Gtk.Button) -> None:
        """Handle start tunnel button click."""
        self._start_tunnel()
    
    def _on_stop_tunnel_clicked(self, button: Gtk.Button) -> None:
        """Handle stop tunnel button click."""
        self._stop_tunnel()

    def _on_copy_url_clicked(self, *args) -> None:
        """Handle copy URL button click."""
        if self.tunnel_manager.is_active():
            url = self.tunnel_manager.get_public_url()
            if url:
                clipboard = Gdk.Display.get_default().get_clipboard()
                clipboard.set(url)
                
                # Show toast notification
                self._show_toast("URL copied to clipboard", timeout=2)
            else:
                self._show_toast("No URL available to copy", timeout=3)
        else:
            self._show_toast("Tunnel is not active", timeout=3)

    def _on_history_button_clicked(self, button: Gtk.Button) -> None:
        """Handle history button click - toggle between history and requests view."""
        current_page = self.main_stack.get_visible_child_name()
        
        if current_page == "history":
            # Currently in history view - go back to requests or empty
            if self.request_rows:
                self.main_stack.set_visible_child_name("requests")
            else:
                self.main_stack.set_visible_child_name("empty")
        else:
            # Currently not in history view - load and show history
            self._load_history()
            self.main_stack.set_visible_child_name("history")
        
        # Update button states
        self._update_history_button_state()

    def _on_clear_button_clicked(self, button: Gtk.Button) -> None:
        """Handle clear button click."""
        self.clear_requests()

    def _on_back_to_requests_clicked(self, button: Gtk.Button) -> None:
        """Handle back to requests button click."""
        # Switch back to requests view
        if self.request_rows:
            self.main_stack.set_visible_child_name("requests")
        else:
            self.main_stack.set_visible_child_name("empty")
        
        # Update button states
        self._update_history_button_state()

    def _on_clear_history_clicked(self, button: Gtk.Button) -> None:
        """Handle clear history button click."""
        self._clear_history()

    def _on_close_request(self, window: Adw.ApplicationWindow) -> bool:
        """Handle window close request."""
        logger.info("Window close request received")
        
        # Save any active requests to history before closing
        if self.request_rows:
            try:
                logger.info(f"Moving {len(self.request_rows)} active requests to history before closing")
                self.storage.clear()  # This moves active requests to history
                logger.info("Successfully moved active requests to history")
            except Exception as e:
                logger.error(f"Error saving requests to history: {e}")
        
        # Stop server and tunnel before closing
        try:
            self.server.stop()
            self.tunnel_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping services: {e}")

        logger.info("Window closing allowed")
        return False  # Allow window to close

    def _on_request_received(self, request: WebhookRequest) -> None:
        """Handle new webhook request (called from background thread)."""
        # Use GLib.idle_add to update UI from main thread
        GLib.idle_add(self._add_request_to_list, request)

    def _add_request_to_list(self, request: WebhookRequest) -> None:
        """Add a request to the list (called from main thread)."""
        # Create request row
        row = RequestRow(request)

        # Connect to expansion signal for accordion behavior
        row.connect("notify::expanded", self._on_row_expanded)

        # Add to tracking list and UI list
        self.request_rows.insert(0, row)  # Insert at beginning to match prepend
        self.request_list.prepend(row)

        # Expand the new row and close all others
        self._expand_single_row(row)

        # Switch to requests view if needed
        if self.main_stack.get_visible_child_name() == "empty":
            self.main_stack.set_visible_child_name("requests")

        # Show banner after first webhook is received
        if not self.has_received_webhooks:
            self.has_received_webhooks = True
            self._update_banner_visibility()

        # Show toast for new request (brief notification)
        self._show_toast(f"New {request.method} request received", timeout=1)
        logger.info(f"Added request to list: {request.method} {request.path}")
        
        # Update button state in case we switched from empty to requests view
        self._update_history_button_state()

    def _update_banner_visibility(self) -> None:
        """Update banner visibility based on tunnel status and webhook history."""
        status = self.tunnel_manager.get_status()
        
        # Only show banner if we have received webhooks and tunnel is active
        if self.has_received_webhooks and status.active and status.public_url:
            self.status_banner.set_title(f"Tunnel active: {status.public_url}")
            self.status_banner.set_revealed(True)
            # Show header stop button when we have received webhooks
            self.header_stop_button.set_visible(True)
        else:
            self.status_banner.set_revealed(False)
            # Hide header stop button when no webhooks or tunnel inactive
            if not self.has_received_webhooks:
                self.header_stop_button.set_visible(False)

    def _on_row_expanded(self, row: RequestRow, pspec) -> None:
        """Handle row expansion for accordion behavior."""
        if row.get_expanded():
            # This row was expanded, close all others
            self._expand_single_row(row)

    def _expand_single_row(self, target_row: RequestRow) -> None:
        """Expand a single row and close all others."""
        for row in self.request_rows:
            if row == target_row:
                row.set_expanded(True)
            else:
                row.set_expanded(False)

    def _update_ui_state(self) -> None:
        """Update UI state based on tunnel status with improved error handling."""
        # Check auth token availability first (don't rely on cached tunnel status)
        import os
        auth_token = os.getenv("NGROK_AUTHTOKEN")
        if not auth_token:
            # Try loading from config file
            try:
                config_file = os.path.expanduser("~/.config/echo/config")
                if os.path.exists(config_file):
                    with open(config_file, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("NGROK_AUTHTOKEN="):
                                auth_token = line.split("=", 1)[1].strip()
                                break
            except Exception:
                pass
        
        # Hide all buttons first
        self.setup_token_button.set_visible(False)
        self.start_tunnel_container.set_visible(False)
        self.copy_url_button.set_visible(False)
        self.stop_tunnel_button.set_visible(False)
        
        # If no auth token, show setup button
        if not auth_token:
            self.setup_token_button.set_visible(True)
            self.url_label.set_text("Setup required: Click 'Setup Ngrok Token' to get started")
            self.tunnel_active = False
            self._update_banner_visibility()
            return
        
        # Get tunnel status for further decisions
        status = self.tunnel_manager.get_status()
        
        # Check if tunnel is unavailable (ngrok not available or other errors)
        if status.error and "not available" in status.error.lower():
            # Ngrok not available - show user-friendly message
            self.url_label.set_text("Ngrok is required but not available. Please install ngrok to continue.")
            self.tunnel_active = False
        elif status.active and status.public_url:
            # Tunnel is active - show copy + stop buttons
            self.copy_url_button.set_visible(True)
            self.stop_tunnel_button.set_visible(True)
            self.url_label.set_text(status.public_url)
            self.tunnel_active = True
        else:
            # Tunnel is inactive but auth token is available - show start button
            self.start_tunnel_container.set_visible(True)
            if status.error and "token" not in status.error.lower():
                # Show specific error if not token-related
                error_msg = status.error[:100] + "..." if len(status.error) > 100 else status.error
                self.url_label.set_text(f"Error: {error_msg}")
            else:
                self.url_label.set_text("Click 'Start Tunnel' to begin receiving webhooks")
            self.tunnel_active = False
        
        # Update banner visibility based on webhook history
        self._update_banner_visibility()


    def _start_tunnel(self) -> None:
        """Start the tunnel in a background thread with improved error handling."""
        # Set loading state immediately
        self._set_tunnel_loading(True)
        
        def start_services():
            try:
                # Start server first
                self.server.start(port=self.server_port)

                # Start tunnel
                status = self.tunnel_manager.start(port=self.server_port)

                # Update UI from main thread
                GLib.idle_add(self._tunnel_start_completed, status)

            except Exception as e:
                logger.error(f"Error starting services: {e}")
                user_error = process_error(str(e), "starting services")
                GLib.idle_add(self._tunnel_start_failed, user_error)

        # Start in background thread
        thread = threading.Thread(target=start_services, daemon=True)
        thread.start()

    def _tunnel_start_completed(self, status) -> None:
        """Handle tunnel start completion (called from main thread)."""
        # Clear loading state
        self._set_tunnel_loading(False)
        
        # Update UI state
        self._update_ui_state()
        
        if status.active:
            logger.info(f"Services started successfully: {status.public_url}")
            self._show_toast("Tunnel started successfully", 3)
        else:
            logger.error(f"Failed to start tunnel: {status.error}")
            # Show user-friendly error dialog
            if status.error:
                user_error = process_error(status.error, "starting tunnel")
                self._show_tunnel_error(user_error)

    def _tunnel_start_failed(self, user_error) -> None:
        """Handle tunnel start failure (called from main thread)."""
        # Clear loading state
        self._set_tunnel_loading(False)
        
        # Update UI state
        self._update_ui_state()
        
        # Show error dialog
        self._show_tunnel_error(user_error)
    
    def _show_tunnel_error(self, user_error) -> None:
        """Show a user-friendly error dialog for tunnel errors."""
        def on_action_callback(action_name):
            """Handle error dialog actions."""
            if action_name == "setup_ngrok_token":
                self._show_token_setup_dialog()
            elif action_name == "open_preferences":
                self._show_token_setup_dialog()
        
        # Show error dialog with action button if available
        show_error_dialog(self, user_error, on_action_callback)

    def _stop_tunnel(self) -> None:
        """Stop the tunnel in a background thread."""
        # Disable stop button during operation
        self.stop_tunnel_button.set_sensitive(False)
        self.header_stop_button.set_sensitive(False)
        
        def stop_services():
            try:
                # Stop tunnel
                self.tunnel_manager.stop()

                # Stop server
                self.server.stop()

                # Update UI from main thread
                GLib.idle_add(self._tunnel_stop_completed)

            except Exception as e:
                logger.error(f"Error stopping services: {e}")
                GLib.idle_add(self._tunnel_stop_failed)

        # Stop in background thread
        thread = threading.Thread(target=stop_services, daemon=True)
        thread.start()

    def _tunnel_stop_completed(self) -> None:
        """Handle tunnel stop completion (called from main thread)."""
        # Re-enable buttons
        self.stop_tunnel_button.set_sensitive(True)
        self.header_stop_button.set_sensitive(True)
        
        # Update UI state
        self._update_ui_state()
        
        # Show toast notification
        self._show_toast("Tunnel stopped", 2)
        logger.info("Services stopped successfully")

    def _tunnel_stop_failed(self) -> None:
        """Handle tunnel stop failure (called from main thread)."""
        # Re-enable buttons
        self.stop_tunnel_button.set_sensitive(True)
        self.header_stop_button.set_sensitive(True)
        
        # Update UI state
        self._update_ui_state()
        
        # Show error toast
        self._show_toast("Failed to stop tunnel", 3)
        logger.error("Failed to stop tunnel")

    def clear_requests(self) -> None:
        """Clear all requests from the list."""
        # Set loading state
        self._set_clear_loading(True)
        
        def clear_operation():
            try:
                # Clear storage
                self.storage.clear()

                # Update UI from main thread
                GLib.idle_add(self._clear_requests_completed)
                
            except Exception as e:
                logger.error(f"Error clearing requests: {e}")
                GLib.idle_add(self._clear_requests_failed)

        # Run in background thread to prevent UI blocking
        thread = threading.Thread(target=clear_operation, daemon=True)
        thread.start()

    def _clear_requests_completed(self) -> None:
        """Handle clear requests completion (called from main thread)."""
        # Clear loading state
        self._set_clear_loading(False)
        
        # Clear tracking list
        self.request_rows.clear()

        # Clear UI list
        while True:
            row = self.request_list.get_first_child()
            if row is None:
                break
            self.request_list.remove(row)

        # Reset webhook flag and hide banner/header button
        self.has_received_webhooks = False
        self.header_stop_button.set_visible(False)
        self._update_banner_visibility()

        # Switch to empty view
        self.main_stack.set_visible_child_name("empty")

        # Show toast notification
        self._show_toast("All requests cleared", timeout=2)
        
        # Update history button visibility and state
        self._update_history_button_visibility()

    def _clear_requests_failed(self) -> None:
        """Handle clear requests failure (called from main thread)."""
        # Clear loading state
        self._set_clear_loading(False)
        
        # Show error toast
        self._show_toast("Failed to clear requests", timeout=3)
        logger.error("Failed to clear requests")

    def _load_history(self) -> None:
        """Load history into the history list."""
        # Clear existing history rows and reset filters
        self._clear_history_list()
        self._current_search_query = ""
        self._current_method_filter = None
        
        # Reset search entry and filter dropdown
        self.history_search_entry.set_text("")
        self.history_method_filter.set_selected(0)
        
        # Get history from storage
        history_requests = self.storage.get_history()
        
        if not history_requests:
            return
        
        # Add history rows
        for request in history_requests:
            row = self._create_history_row(request)
            self.history_rows.append(row)
            self.history_list.append(row)

    def _create_history_row(self, request):
        """Create a history row with restore/delete buttons."""
        from .request_row import RequestRow
        
        # Create a modified request row for history
        row = RequestRow(request)
        
        # Add restore and delete buttons to the row
        restore_button = Gtk.Button(
            icon_name="edit-undo-symbolic",
            tooltip_text="Restore to active requests"
        )
        restore_button.add_css_class("flat")
        restore_button.connect("clicked", lambda btn, req_id=request.id: self._restore_from_history(req_id))
        
        delete_button = Gtk.Button(
            icon_name="edit-delete-symbolic", 
            tooltip_text="Delete permanently"
        )
        delete_button.add_css_class("flat")
        delete_button.add_css_class("destructive-action")
        delete_button.connect("clicked", lambda btn, req_id=request.id: self._delete_from_history(req_id))
        
        # Add buttons to the row's action area (we'll need to modify RequestRow for this)
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.append(restore_button)
        button_box.append(delete_button)
        
        # For now, just return the basic row - we can enhance this later
        return row

    def _restore_from_history(self, request_id: str) -> None:
        """Restore a request from history to active requests."""
        if self.storage.restore_from_history(request_id):
            # Find and remove the row from both lists
            for i, row in enumerate(self.history_rows):
                if row.get_request().id == request_id:
                    self.history_list.remove(row)
                    del self.history_rows[i]
                    break
            
            for i, row in enumerate(self.filtered_history_rows):
                if row.get_request().id == request_id:
                    del self.filtered_history_rows[i]
                    break
            
            # Refresh the requests view to show the restored request
            self._refresh_requests_view()
            
            # Show success toast
            self._show_toast("Request restored to active requests", timeout=2)
            
            # Update history button visibility
            self._update_history_button_visibility()

    def _delete_from_history(self, request_id: str) -> None:
        """Permanently delete a request from history."""
        if self.storage.remove_from_history(request_id):
            # Find and remove the row from both lists
            for i, row in enumerate(self.history_rows):
                if row.get_request().id == request_id:
                    self.history_list.remove(row)
                    del self.history_rows[i]
                    break
            
            for i, row in enumerate(self.filtered_history_rows):
                if row.get_request().id == request_id:
                    del self.filtered_history_rows[i]
                    break
            
            # Show success toast
            self._show_toast("Request deleted permanently", timeout=2)
            
            # Update history button visibility
            self._update_history_button_visibility()

    def _clear_history(self) -> None:
        """Clear all history."""
        self.storage.clear_history()
        self._clear_history_list()
        self._show_toast("All history cleared", timeout=2)
        self._update_history_button_visibility()

    def _clear_history_list(self) -> None:
        """Clear the history list UI."""
        self.history_rows.clear()
        self.filtered_history_rows.clear()
        while True:
            row = self.history_list.get_first_child()
            if row is None:
                break
            self.history_list.remove(row)

    def _refresh_requests_view(self) -> None:
        """Refresh the requests view to show any restored requests."""
        # This is a simple refresh - we could optimize this later
        pass

    def _update_history_button_visibility(self) -> None:
        """Update history button visibility based on whether there's history."""
        has_history = self.storage.count_history() > 0
        # Header history button is always visible if there's history
        self.header_history_button.set_visible(has_history)
        # Requests page history button only visible when there's history and active requests
        self.history_button.set_visible(has_history and len(self.request_rows) > 0)
        
        # Update button state
        self._update_history_button_state()
        
    def _update_history_button_state(self) -> None:
        """Update history button appearance based on current view state."""
        current_page = self.main_stack.get_visible_child_name()
        is_in_history = current_page == "history"
        
        if is_in_history:
            # In history view - only change tooltip
            self.header_history_button.set_tooltip_text("Close History")
        else:
            # Not in history view - show "open" state  
            self.header_history_button.set_tooltip_text("View History")
        
    def _setup_method_filter(self) -> None:
        """Set up the method filter dropdown."""
        from gi.repository import Gio
        
        # Create string list model with common HTTP methods
        string_list = Gio.ListStore.new(Gtk.StringObject)
        string_list.append(Gtk.StringObject.new("All Methods"))
        string_list.append(Gtk.StringObject.new("GET"))
        string_list.append(Gtk.StringObject.new("POST"))
        string_list.append(Gtk.StringObject.new("PUT"))
        string_list.append(Gtk.StringObject.new("PATCH"))
        string_list.append(Gtk.StringObject.new("DELETE"))
        string_list.append(Gtk.StringObject.new("HEAD"))
        string_list.append(Gtk.StringObject.new("OPTIONS"))
        
        self.history_method_filter.set_model(string_list)
        self.history_method_filter.set_selected(0)  # Default to "All Methods"
        
    def _on_history_stats_clicked(self, button: Gtk.Button) -> None:
        """Handle history stats button click."""
        self._show_history_stats_dialog()
        
    def _on_export_history_clicked(self, button: Gtk.Button) -> None:
        """Handle export history button click."""
        self._show_export_dialog()
        
    def _on_search_changed(self, search_entry: Gtk.SearchEntry) -> None:
        """Handle search entry text changes."""
        self._current_search_query = search_entry.get_text()
        self._filter_history()
        
    def _on_method_filter_changed(self, dropdown: Gtk.DropDown, pspec) -> None:
        """Handle method filter dropdown changes."""
        selected = dropdown.get_selected()
        if selected == 0:  # "All Methods"
            self._current_method_filter = None
        else:
            # Get the selected method string
            model = dropdown.get_model()
            string_obj = model.get_item(selected)
            self._current_method_filter = string_obj.get_string()
        
        self._filter_history()
        
    def _filter_history(self) -> None:
        """Filter the history list based on current search and method filter."""
        # Clear existing filtered results
        self._clear_history_list()
        
        # Get filtered results from storage
        filtered_requests = self.storage.search_history(
            query=self._current_search_query,
            method=self._current_method_filter
        )
        
        # Add filtered rows to the list
        for request in filtered_requests:
            row = self._create_history_row(request)
            self.filtered_history_rows.append(row)
            self.history_list.append(row)
    
    def _show_history_stats_dialog(self) -> None:
        """Show a dialog with history statistics."""
        stats = self.storage.get_history_stats()
        
        # Create a dialog to show stats
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading("History Statistics")
        
        # Build stats text
        stats_text = f"Total Requests: {stats['total_requests']}\n\n"
        
        if stats['methods']:
            stats_text += "Methods:\n"
            for method, count in stats['methods'].items():
                stats_text += f"  {method}: {count}\n"
            stats_text += "\n"
        
        if stats['date_range']:
            date_range = stats['date_range']
            stats_text += f"Date Range: {date_range['span_days']} days\n"
            stats_text += f"Average per day: {stats['average_requests_per_day']}\n\n"
        
        if stats['most_common_paths']:
            stats_text += "Most Common Paths:\n"
            for path, count in stats['most_common_paths'][:5]:  # Top 5
                stats_text += f"  {path}: {count}\n"
        
        dialog.set_body(stats_text)
        dialog.add_response("close", "Close")
        dialog.set_default_response("close")
        
        dialog.present()
    
    def _show_export_dialog(self) -> None:
        """Show a file chooser dialog to export history."""
        from gi.repository import Gio
        
        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title="Export History",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE
        )
        
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Export", Gtk.ResponseType.ACCEPT)
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)
        
        # Add file filters
        json_filter = Gtk.FileFilter()
        json_filter.set_name("JSON files")
        json_filter.add_pattern("*.json")
        dialog.add_filter(json_filter)
        
        csv_filter = Gtk.FileFilter()
        csv_filter.set_name("CSV files")
        csv_filter.add_pattern("*.csv")
        dialog.add_filter(csv_filter)
        
        txt_filter = Gtk.FileFilter()
        txt_filter.set_name("Text files")
        txt_filter.add_pattern("*.txt")
        dialog.add_filter(txt_filter)
        
        # Set default filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dialog.set_current_name(f"echo_history_{timestamp}.json")
        
        def on_response(dialog, response):
            if response == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                if file:
                    filepath = file.get_path()
                    # Determine format from extension
                    if filepath.endswith('.csv'):
                        format_type = 'csv'
                    elif filepath.endswith('.txt'):
                        format_type = 'txt'
                    else:
                        format_type = 'json'
                    
                    # Perform export
                    success = self.storage.export_history(filepath, format_type)
                    if success:
                        self._show_toast(f"History exported to {filepath}", timeout=3)
                    else:
                        self._show_toast("Failed to export history", timeout=3)
            
            dialog.destroy()
        
        dialog.connect("response", on_response)
        dialog.present()

    def _show_token_setup_dialog(self) -> None:
        """Show dialog to help user set up ngrok auth token."""
        from .preferences import PreferencesDialog
        
        # Create and show preferences dialog with UI update callback
        preferences = PreferencesDialog(
            parent=self, 
            tunnel_manager=self.tunnel_manager,
            ui_update_callback=self._update_ui_state
        )
        preferences.present(self)
        
        # Connect to dialog close event to refresh UI
        preferences.connect("closed", self._on_preferences_closed)
        
        # Show a helpful message
        logger.info("Opening preferences to help user set up ngrok auth token")
    
    def _on_preferences_closed(self, dialog) -> None:
        """Handle preferences dialog close."""
        # Simply update UI state - the _update_ui_state method now checks auth token directly
        self._update_ui_state()
        logger.info("Preferences dialog closed, UI state refreshed")

    def get_tunnel_status(self) -> TunnelStatus:
        """Get the current tunnel status."""
        return self.tunnel_manager.get_status()

    def get_request_count(self) -> int:
        """Get the number of stored requests."""
        return self.storage.count()

    def copy_tunnel_url(self) -> None:
        """Copy the tunnel URL to clipboard (keyboard shortcut handler)."""
        if self.tunnel_manager.is_active():
            url = self.tunnel_manager.get_public_url()
            if url:
                clipboard = Gdk.Display.get_default().get_clipboard()
                clipboard.set(url)
                self._show_toast("URL copied to clipboard", timeout=2)
            else:
                self._show_toast("No URL available to copy", timeout=3)
        else:
            self._show_toast("Tunnel is not active", timeout=3)
    
    def toggle_tunnel(self) -> None:
        """Toggle tunnel state (start/stop) via keyboard shortcut."""
        if self.tunnel_manager.is_active():
            self._stop_tunnel()
            self._show_toast("Stopping tunnel...", timeout=2)
        else:
            self._start_tunnel()
            self._show_toast("Starting tunnel...", timeout=2)
    
    def refresh_ui(self) -> None:
        """Refresh the UI state (keyboard shortcut handler)."""
        self._update_ui_state()
    
    def toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode (keyboard shortcut handler)."""
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()
    
    def copy_focused_request(self) -> None:
        """Copy data from the currently focused request (keyboard shortcut handler)."""
        # Find the currently expanded request row
        focused_row = None
        for row in self.request_rows:
            if row.get_expanded():
                focused_row = row
                break
        
        if focused_row:
            # Trigger the copy button click on the focused row
            focused_row._on_copy_clicked(None)
            self._show_toast("Request data copied to clipboard", timeout=2)
        else:
            # If no row is expanded, copy the most recent request
            if self.request_rows:
                most_recent = self.request_rows[0]  # First in list is most recent
                most_recent._on_copy_clicked(None)
                self._show_toast("Latest request data copied to clipboard", timeout=2)
            else:
                self._show_toast("No requests available to copy", timeout=3)
