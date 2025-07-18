"""
Error handling utilities for user-friendly error messages and recovery.
"""

import re
from typing import Dict, List, Optional, Tuple, Union

from .logging_config import get_logger

logger = get_logger(__name__)


class ErrorCategory:
    """Error categories for better user experience."""
    NETWORK = "network"
    AUTH = "authentication"
    CONFIG = "configuration"
    VALIDATION = "validation"
    SYSTEM = "system"
    TUNNEL = "tunnel"
    SERVER = "server"


class ErrorSeverity:
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


class UserError:
    """User-friendly error representation."""
    
    def __init__(
        self,
        title: str,
        message: str,
        category: str,
        severity: str = ErrorSeverity.ERROR,
        suggestions: Optional[List[str]] = None,
        technical_details: Optional[str] = None,
        recoverable: bool = True,
        action_label: Optional[str] = None,
        action_callback: Optional[str] = None
    ):
        self.title = title
        self.message = message
        self.category = category
        self.severity = severity
        self.suggestions = suggestions or []
        self.technical_details = technical_details
        self.recoverable = recoverable
        self.action_label = action_label
        self.action_callback = action_callback


class ErrorHandler:
    """Handles error processing and user-friendly message generation."""
    
    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
    
    def _initialize_error_patterns(self) -> Dict[str, Dict]:
        """Initialize patterns for recognizing common errors."""
        return {
            # Network errors
            r"connection.*refused|connection.*failed": {
                "category": ErrorCategory.NETWORK,
                "title": "Connection Failed",
                "message": "Unable to connect to the service.",
                "suggestions": [
                    "Check your internet connection",
                    "Verify the server is running",
                    "Try again in a few moments"
                ]
            },
            r"timeout|timed out": {
                "category": ErrorCategory.NETWORK,
                "title": "Connection Timeout",
                "message": "The connection took too long to establish.",
                "suggestions": [
                    "Check your internet connection",
                    "Try again with a stable network",
                    "Contact your network administrator if this persists"
                ]
            },
            r"name resolution failed|name or service not known": {
                "category": ErrorCategory.NETWORK,
                "title": "Network Error",
                "message": "Cannot resolve the server address.",
                "suggestions": [
                    "Check your DNS settings",
                    "Verify your internet connection",
                    "Try connecting to a different network"
                ]
            },
            
            # Ngrok/Tunnel errors
            r"invalid.*authtoken|authtoken.*invalid": {
                "category": ErrorCategory.AUTH,
                "title": "Invalid Ngrok Token",
                "message": "Your ngrok authentication token is invalid or expired.",
                "suggestions": [
                    "Check your ngrok auth token in the settings",
                    "Get a new token from ngrok.com",
                    "Ensure the token is copied correctly without extra spaces"
                ],
                "action_label": "Open Settings",
                "action_callback": "open_preferences"
            },
            r"authtoken.*not.*found|NGROK_AUTHTOKEN": {
                "category": ErrorCategory.CONFIG,
                "title": "Ngrok Token Required",
                "message": "An ngrok authentication token is required to create tunnels.",
                "suggestions": [
                    "Sign up for a free account at ngrok.com",
                    "Copy your auth token from the ngrok dashboard",
                    "Add the token in Sonar's settings"
                ],
                "action_label": "Setup Token",
                "action_callback": "setup_ngrok_token"
            },
            r"tunnel.*session.*failed|failed.*to.*establish.*tunnel": {
                "category": ErrorCategory.TUNNEL,
                "title": "Tunnel Connection Failed",
                "message": "Unable to establish a tunnel connection.",
                "suggestions": [
                    "Check your internet connection",
                    "Verify your ngrok auth token is valid",
                    "Try again in a few moments"
                ]
            },
            r"port.*already.*in.*use|address.*already.*in.*use": {
                "category": ErrorCategory.SERVER,
                "title": "Port Already in Use",
                "message": "The selected port is already being used by another application.",
                "suggestions": [
                    "Close other applications using this port",
                    "Try restarting Sonar",
                    "Check if another instance of Sonar is running"
                ]
            },
            r"rate.*limit|too.*many.*requests": {
                "category": ErrorCategory.TUNNEL,
                "title": "Rate Limit Exceeded",
                "message": "Too many tunnel requests. Please wait before trying again.",
                "suggestions": [
                    "Wait a few minutes before retrying",
                    "Consider upgrading your ngrok plan for higher limits",
                    "Avoid creating tunnels too frequently"
                ]
            },
            r"ngrok.*not.*available|ngrok.*not.*found": {
                "category": ErrorCategory.SYSTEM,
                "title": "Ngrok Not Available",
                "message": "Ngrok is not installed or not accessible.",
                "suggestions": [
                    "Install ngrok from ngrok.com",
                    "Ensure ngrok is in your system PATH",
                    "Try restarting Sonar after installation"
                ]
            },
            
            # Permission errors
            r"permission.*denied|access.*denied": {
                "category": ErrorCategory.SYSTEM,
                "title": "Permission Denied",
                "message": "Sonar doesn't have permission to perform this action.",
                "suggestions": [
                    "Run Sonar with appropriate permissions",
                    "Check file and directory permissions",
                    "Try running as administrator if necessary"
                ]
            },
            
            # Validation errors
            r"invalid.*port|port.*invalid": {
                "category": ErrorCategory.VALIDATION,
                "title": "Invalid Port",
                "message": "The specified port number is invalid.",
                "suggestions": [
                    "Use a port number between 1 and 65535",
                    "Avoid well-known ports (1-1023) unless necessary",
                    "Try a port in the range 8000-9999"
                ]
            }
        }
    
    def process_error(
        self, 
        error: Union[str, Exception], 
        context: Optional[str] = None
    ) -> UserError:
        """Process an error and return a user-friendly representation."""
        
        error_text = str(error).lower()
        
        # Try to match against known patterns
        for pattern, error_info in self.error_patterns.items():
            if re.search(pattern, error_text):
                return UserError(
                    title=error_info["title"],
                    message=error_info["message"],
                    category=error_info["category"],
                    suggestions=error_info["suggestions"],
                    technical_details=str(error),
                    action_label=error_info.get("action_label"),
                    action_callback=error_info.get("action_callback")
                )
        
        # Fallback for unrecognized errors
        return self._create_generic_error(error, context)
    
    def _create_generic_error(
        self, 
        error: Union[str, Exception], 
        context: Optional[str] = None
    ) -> UserError:
        """Create a generic error for unrecognized errors."""
        
        error_str = str(error)
        
        # Try to extract meaningful information
        if "connection" in error_str.lower():
            category = ErrorCategory.NETWORK
            title = "Connection Error"
            suggestions = [
                "Check your internet connection",
                "Try again in a few moments",
                "Contact support if this persists"
            ]
        elif "auth" in error_str.lower() or "token" in error_str.lower():
            category = ErrorCategory.AUTH
            title = "Authentication Error"
            suggestions = [
                "Check your authentication credentials",
                "Verify your token is valid",
                "Try refreshing your authentication"
            ]
        elif "config" in error_str.lower() or "setting" in error_str.lower():
            category = ErrorCategory.CONFIG
            title = "Configuration Error"
            suggestions = [
                "Check your settings",
                "Reset to default configuration if needed",
                "Verify all required fields are filled"
            ]
        else:
            category = ErrorCategory.SYSTEM
            title = "Unexpected Error"
            suggestions = [
                "Try restarting the application",
                "Check the application logs for more details",
                "Contact support if this error persists"
            ]
        
        context_msg = f" while {context}" if context else ""
        
        return UserError(
            title=title,
            message=f"An error occurred{context_msg}. Please try again.",
            category=category,
            suggestions=suggestions,
            technical_details=error_str
        )
    
    def validate_port(self, port: Union[str, int]) -> Tuple[bool, Optional[UserError]]:
        """Validate a port number."""
        try:
            port_num = int(port)
            if port_num < 1 or port_num > 65535:
                return False, UserError(
                    title="Invalid Port",
                    message=f"Port {port_num} is outside the valid range.",
                    category=ErrorCategory.VALIDATION,
                    suggestions=[
                        "Use a port number between 1 and 65535",
                        "Try a port in the range 8000-9999 for development"
                    ]
                )
            
            if port_num < 1024:
                return True, UserError(
                    title="Privileged Port Warning",
                    message=f"Port {port_num} requires elevated privileges.",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.WARNING,
                    suggestions=[
                        "Use a port number above 1024 to avoid permission issues",
                        "Run with administrator privileges if you need this port"
                    ]
                )
            
            return True, None
            
        except ValueError:
            return False, UserError(
                title="Invalid Port Format",
                message="Port must be a valid number.",
                category=ErrorCategory.VALIDATION,
                suggestions=[
                    "Enter a numeric port value",
                    "Use a port between 1 and 65535"
                ]
            )
    
    def validate_ngrok_token(self, token: str) -> Tuple[bool, Optional[UserError]]:
        """Validate an ngrok auth token format."""
        if not token or not token.strip():
            return False, UserError(
                title="Empty Token",
                message="Ngrok auth token cannot be empty.",
                category=ErrorCategory.VALIDATION,
                suggestions=[
                    "Get your auth token from ngrok.com",
                    "Copy the token from your ngrok dashboard"
                ]
            )
        
        token = token.strip()
        
        # Basic format validation (ngrok tokens are typically alphanumeric with underscores)
        if not re.match(r'^[A-Za-z0-9_]+$', token):
            return False, UserError(
                title="Invalid Token Format",
                message="The auth token contains invalid characters.",
                category=ErrorCategory.VALIDATION,
                suggestions=[
                    "Ensure you copied the complete token",
                    "Check for extra spaces or special characters",
                    "Get a fresh token from ngrok.com if needed"
                ]
            )
        
        # Length check (ngrok tokens are usually quite long)
        if len(token) < 20:
            return True, UserError(
                title="Short Token Warning",
                message="This token seems shorter than expected.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.WARNING,
                suggestions=[
                    "Verify you copied the complete token",
                    "Check your ngrok dashboard for the correct token"
                ]
            )
        
        return True, None
    
    def should_retry_error(self, error: UserError) -> bool:
        """Determine if an error condition should allow retry."""
        retry_categories = {
            ErrorCategory.NETWORK,
            ErrorCategory.TUNNEL,
            ErrorCategory.SERVER
        }
        
        # Don't retry validation or auth errors without user action
        if error.category in {ErrorCategory.VALIDATION, ErrorCategory.AUTH}:
            return False
        
        return error.category in retry_categories and error.recoverable


# Global error handler instance
error_handler = ErrorHandler()


def process_error(
    error: Union[str, Exception], 
    context: Optional[str] = None
) -> UserError:
    """Convenience function to process errors."""
    return error_handler.process_error(error, context)


def validate_port(port: Union[str, int]) -> Tuple[bool, Optional[UserError]]:
    """Convenience function to validate ports."""
    return error_handler.validate_port(port)


def validate_ngrok_token(token: str) -> Tuple[bool, Optional[UserError]]:
    """Convenience function to validate ngrok tokens."""
    return error_handler.validate_ngrok_token(token)