"""
Error dialog utilities for displaying user-friendly errors in the UI.
"""

from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from .error_handler import UserError, ErrorSeverity
from .logging_config import get_logger

logger = get_logger(__name__)


class ErrorDialog:
    """Helper class for displaying user-friendly error dialogs."""
    
    @staticmethod
    def show_error(
        parent: Gtk.Window,
        error: UserError,
        on_action_callback: Optional[callable] = None
    ) -> None:
        """Show an error dialog with user-friendly information."""
        
        # Create the dialog
        dialog = Adw.MessageDialog.new(parent)
        dialog.set_heading(error.title)
        dialog.set_body(error.message)
        
        # Set appropriate icon based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            dialog.add_css_class("error")
        elif error.severity == ErrorSeverity.WARNING:
            dialog.add_css_class("warning")
        
        # Add suggestions if available
        if error.suggestions:
            suggestions_text = "\n".join(f"• {suggestion}" for suggestion in error.suggestions)
            full_body = f"{error.message}\n\n**What you can try:**\n{suggestions_text}"
            dialog.set_body(full_body)
        
        # Add action button if available
        if error.action_label and error.action_callback and on_action_callback:
            dialog.add_response(error.action_callback, error.action_label)
            dialog.set_response_appearance(error.action_callback, Adw.ResponseAppearance.SUGGESTED)
        
        # Add close button
        dialog.add_response("close", "Close")
        dialog.set_default_response("close")
        dialog.set_close_response("close")
        
        # Handle responses
        def on_response(dialog, response_id):
            if response_id == error.action_callback and on_action_callback:
                try:
                    on_action_callback(error.action_callback)
                except Exception as e:
                    logger.error(f"Error in action callback: {e}")
            dialog.destroy()
        
        dialog.connect("response", on_response)
        
        # Show the dialog
        dialog.present()
    
    @staticmethod
    def show_error_toast(
        toast_overlay: Adw.ToastOverlay,
        error: UserError,
        timeout: int = 5
    ) -> None:
        """Show a brief error message as a toast notification."""
        
        # Create toast with error message
        toast = Adw.Toast.new(error.message)
        toast.set_timeout(timeout)
        
        # Add action button for more details if available
        if error.suggestions or error.technical_details:
            toast.set_button_label("Details")
            toast.set_action_name("app.show-error-details")
        
        # Show the toast
        toast_overlay.add_toast(toast)
    
    @staticmethod
    def show_validation_error(
        parent: Gtk.Widget,
        error: UserError,
        target_widget: Optional[Gtk.Widget] = None
    ) -> None:
        """Show a validation error next to a form field."""
        
        # Add error styling to the target widget
        if target_widget:
            target_widget.add_css_class("error")
        
        # For now, show as a simple dialog
        # In the future, this could be enhanced with inline error messages
        ErrorDialog.show_error(parent.get_root(), error)
    
    @staticmethod
    def create_error_banner(
        error: UserError,
        on_action_callback: Optional[callable] = None
    ) -> Adw.Banner:
        """Create a banner widget for displaying errors inline."""
        
        banner = Adw.Banner()
        banner.set_title(error.message)
        
        # Add action button if available
        if error.action_label and error.action_callback and on_action_callback:
            banner.set_button_label(error.action_label)
            
            def on_button_clicked(banner):
                try:
                    on_action_callback(error.action_callback)
                except Exception as e:
                    logger.error(f"Error in banner action callback: {e}")
            
            banner.connect("button-clicked", on_button_clicked)
        
        # Add appropriate styling
        if error.severity == ErrorSeverity.CRITICAL:
            banner.add_css_class("error")
        elif error.severity == ErrorSeverity.WARNING:
            banner.add_css_class("warning")
        
        return banner


class ErrorStatusPage:
    """Helper class for creating error status pages."""
    
    @staticmethod
    def create_error_page(error: UserError) -> Adw.StatusPage:
        """Create a status page for displaying errors."""
        
        status_page = Adw.StatusPage()
        status_page.set_title(error.title)
        status_page.set_description(error.message)
        
        # Set appropriate icon
        if error.severity == ErrorSeverity.CRITICAL:
            status_page.set_icon_name("dialog-error-symbolic")
        elif error.severity == ErrorSeverity.WARNING:
            status_page.set_icon_name("dialog-warning-symbolic")
        else:
            status_page.set_icon_name("dialog-information-symbolic")
        
        # Add suggestions as child content if available
        if error.suggestions:
            suggestions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            suggestions_box.set_halign(Gtk.Align.CENTER)
            
            suggestions_label = Gtk.Label()
            suggestions_label.set_markup("<b>What you can try:</b>")
            suggestions_box.append(suggestions_label)
            
            for suggestion in error.suggestions:
                suggestion_label = Gtk.Label(label=f"• {suggestion}")
                suggestion_label.set_wrap(True)
                suggestion_label.set_max_width_chars(60)
                suggestion_label.add_css_class("caption")
                suggestions_box.append(suggestion_label)
            
            status_page.set_child(suggestions_box)
        
        return status_page


def show_error_dialog(
    parent: Gtk.Window,
    error: UserError,
    on_action_callback: Optional[callable] = None
) -> None:
    """Convenience function for showing error dialogs."""
    ErrorDialog.show_error(parent, error, on_action_callback)


def show_error_toast(
    toast_overlay: Adw.ToastOverlay,
    error: UserError,
    timeout: int = 5
) -> None:
    """Convenience function for showing error toasts."""
    ErrorDialog.show_error_toast(toast_overlay, error, timeout)


def create_error_banner(
    error: UserError,
    on_action_callback: Optional[callable] = None
) -> Adw.Banner:
    """Convenience function for creating error banners."""
    return ErrorDialog.create_error_banner(error, on_action_callback)