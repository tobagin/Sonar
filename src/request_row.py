"""
Request row widget for displaying webhook requests.
"""

import json

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# GTK imports must come after gi.require_version
from gi.repository import Adw, Gdk, GObject, Gtk  # noqa: E402

from .models import WebhookRequest  # noqa: E402
from .input_sanitizer import sanitize_for_display  # noqa: E402
from .logging_config import get_logger  # noqa: E402

logger = get_logger(__name__)


@Gtk.Template(resource_path="/io/github/tobagin/sonar/ui/request_row.ui")
class RequestRow(Adw.ExpanderRow):
    """Widget for displaying a single webhook request."""

    __gtype_name__ = "RequestRow"

    # Template children
    method_label: Gtk.Label = Gtk.Template.Child()
    copy_button: Gtk.Button = Gtk.Template.Child()
    copy_headers_button: Gtk.Button = Gtk.Template.Child()
    copy_body_button: Gtk.Button = Gtk.Template.Child()
    headers_text: Gtk.TextView = Gtk.Template.Child()
    body_text: Gtk.TextView = Gtk.Template.Child()

    # Properties for binding
    method = GObject.Property(type=str, default="")
    path = GObject.Property(type=str, default="")
    method_path = GObject.Property(type=str, default="")
    timestamp_text = GObject.Property(type=str, default="")
    content_type = GObject.Property(type=str, default="")

    def __init__(self, request: WebhookRequest, **kwargs) -> None:
        """Initialize the request row."""
        super().__init__(**kwargs)

        self.request = request

        # Set up the UI
        self._setup_ui()
        self._setup_signals()

        # Populate data
        self._populate_data()

    def _setup_ui(self) -> None:
        """Set up the UI elements."""
        # Set up text views
        self.headers_text.set_editable(False)
        self.headers_text.set_cursor_visible(False)
        self.headers_text.set_monospace(True)

        self.body_text.set_editable(False)
        self.body_text.set_cursor_visible(False)
        self.body_text.set_monospace(True)

        # Set up method label styling
        self._style_method_label()

    def _setup_signals(self) -> None:
        """Set up signal connections."""
        self.copy_button.connect("clicked", self._on_copy_clicked)
        self.copy_headers_button.connect("clicked", self._on_copy_headers_clicked)
        self.copy_body_button.connect("clicked", self._on_copy_body_clicked)

    def _style_method_label(self) -> None:
        """Apply styling to the method label based on HTTP method."""
        method = self.request.method.upper()

        # Remove existing CSS classes
        for css_class in ["success", "warning", "error", "accent"]:
            self.method_label.remove_css_class(css_class)

        # Add appropriate CSS class
        if method == "GET":
            self.method_label.add_css_class("accent")
        elif method == "POST":
            self.method_label.add_css_class("success")
        elif method == "PUT":
            self.method_label.add_css_class("warning")
        elif method == "DELETE":
            self.method_label.add_css_class("error")
        else:
            self.method_label.add_css_class("accent")

    def _populate_data(self) -> None:
        """Populate the widget with request data."""
        # Set properties for binding with sanitization
        self.method = sanitize_for_display(self.request.method, max_length=10)
        self.path = sanitize_for_display(self.request.path, max_length=200)
        self.method_path = sanitize_for_display(f"{self.request.method} {self.request.path}", max_length=250)
        self.timestamp_text = self.request.timestamp.strftime("%H:%M:%S")
        
        content_type_text = self.request.content_type or "Not specified"
        self.content_type = sanitize_for_display(content_type_text, max_length=100)

        # Set headers with sanitization
        headers_buffer = self.headers_text.get_buffer()
        headers_text = sanitize_for_display(self.request.formatted_headers, max_length=10000)
        headers_buffer.set_text(headers_text)

        # Set body with minimal sanitization for display
        body_buffer = self.body_text.get_buffer()
        body_text = self._format_body()
        # For JSON display, avoid over-sanitization that could escape quotes
        if isinstance(self.request.body, (dict, str)) and body_text != "No body":
            # Direct text for JSON - already formatted properly
            body_buffer.set_text(body_text)
        else:
            # Use sanitization for other content types
            sanitized_body = sanitize_for_display(body_text, max_length=50000)
            body_buffer.set_text(sanitized_body)

    def _format_body(self) -> str:
        """Format the request body for display."""
        if not self.request.body:
            return "No body"

        body = self.request.body

        # Handle bytes
        if isinstance(body, bytes):
            try:
                body = body.decode('utf-8')
            except UnicodeDecodeError:
                return f"<binary data: {len(body)} bytes>"

        # Try to pretty-format JSON
        if isinstance(body, dict):
            try:
                return json.dumps(body, indent=2, ensure_ascii=False)
            except Exception:
                return str(body)

        # Try to parse and format JSON string
        if isinstance(body, str):
            try:
                parsed = json.loads(body)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                return body

        return str(body)

    def _on_copy_clicked(self, button: Gtk.Button) -> None:
        """Handle copy button click."""
        # Create comprehensive request data
        request_data = {
            "id": self.request.id,
            "timestamp": self.request.timestamp.isoformat(),
            "method": self.request.method,
            "path": self.request.path,
            "headers": self.request.headers,
            "query_params": self.request.query_params,
            "body": self.request.body,
            "content_type": self.request.content_type,
            "content_length": self.request.content_length
        }

        # Convert to JSON
        try:
            json_data = json.dumps(request_data, indent=2, ensure_ascii=False, default=str)

            # Copy to clipboard
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(json_data)

            # Note: Toast notifications are handled by the calling code

        except Exception as e:
            logger.error(f"Error copying request data: {e}")

    def _on_copy_headers_clicked(self, button: Gtk.Button) -> None:
        """Handle copy headers button click."""
        try:
            headers_text = self.request.formatted_headers
            
            # Copy to clipboard
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(headers_text)
            
        except Exception as e:
            logger.error(f"Error copying headers: {e}")

    def _on_copy_body_clicked(self, button: Gtk.Button) -> None:
        """Handle copy body button click."""
        try:
            body_text = self._format_body()
            
            # Copy to clipboard
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(body_text)
            
        except Exception as e:
            logger.error(f"Error copying body: {e}")

    def get_request(self) -> WebhookRequest:
        """Get the associated webhook request."""
        return self.request

    def update_request(self, request: WebhookRequest) -> None:
        """Update the widget with new request data."""
        self.request = request
        self._populate_data()
        self._style_method_label()

    def get_formatted_curl(self) -> str:
        """Get a curl command representation of the request."""
        curl_parts = [f"curl -X {self.request.method}"]

        # Add headers
        for key, value in self.request.headers.items():
            curl_parts.append(f'-H "{key}: {value}"')

        # Add query parameters
        if self.request.query_params:
            query_string = "&".join(f"{k}={v}" for k, v in self.request.query_params.items())
            path_with_query = f"{self.request.path}?{query_string}"
        else:
            path_with_query = self.request.path

        # Add body
        if self.request.body:
            body_str = self.request.body
            if isinstance(body_str, bytes):
                body_str = body_str.decode('utf-8', errors='replace')
            elif isinstance(body_str, dict):
                body_str = json.dumps(body_str)

            curl_parts.append(f"-d '{body_str}'")

        # Add URL (placeholder)
        curl_parts.append(f'"https://example.com{path_with_query}"')

        return " \\\n  ".join(curl_parts)

    def get_summary(self) -> str:
        """Get a summary of the request."""
        return f"{self.request.method} {self.request.path} at {self.timestamp_text}"
