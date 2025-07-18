"""
Ngrok tunnel manager for creating public URLs.
"""

import os
import threading

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        pass

# Make ngrok imports optional
try:
    from pyngrok import ngrok
    from pyngrok.conf import PyngrokConfig
    from pyngrok.exception import PyngrokError
    NGROK_AVAILABLE = True
except ImportError:
    NGROK_AVAILABLE = False
    # Create dummy classes/functions for when ngrok is not available
    class PyngrokError(Exception):
        pass
    
    class ngrok:
        @staticmethod
        def set_auth_token(token):
            pass
        
        @staticmethod
        def connect(port, proto="http", pyngrok_config=None):
            return None
        
        @staticmethod
        def disconnect(url):
            pass
        
        @staticmethod
        def get_tunnels():
            return []
        
        @staticmethod
        def kill():
            pass
    
    class PyngrokConfig:
        def __init__(self, **kwargs):
            pass

from .models import TunnelStatus
from .error_handler import process_error, validate_port, ErrorCategory
from .logging_config import get_logger

logger = get_logger(__name__)


class TunnelManager:
    """Manages ngrok tunnels for the webhook server."""

    def __init__(self) -> None:
        """Initialize the tunnel manager."""
        load_dotenv()
        self.tunnel = None
        self.status = TunnelStatus()
        self._lock = threading.Lock()
        self.auth_token_set = False

        # Check if ngrok is available
        if not NGROK_AVAILABLE:
            logger.warning("Ngrok is not available - tunnel features disabled")
            self.status = TunnelStatus(
                active=False,
                error="Ngrok is not available. Install pyngrok to enable tunnel features."
            )
            return

        # Configure ngrok
        auth_token = self._load_auth_token()
        if auth_token:
            try:
                ngrok.set_auth_token(auth_token)
                self.auth_token_set = True
                logger.info("Ngrok auth token set successfully")
            except Exception as e:
                logger.error(f"Failed to set ngrok auth token: {e}")
                self.status = TunnelStatus(
                    active=False,
                    error=f"Failed to set ngrok auth token: {e}"
                )
        else:
            logger.warning("No NGROK_AUTHTOKEN found in environment")
            self.status = TunnelStatus(
                active=False,
                error="No NGROK_AUTHTOKEN found in environment. Set NGROK_AUTHTOKEN to use tunnel features."
            )

    def _load_auth_token(self) -> str | None:
        """Load auth token from environment or config file."""
        # First try environment variable
        auth_token = os.getenv("NGROK_AUTHTOKEN")
        if auth_token:
            return auth_token
        
        # Then try config file
        try:
            config_file = os.path.expanduser("~/.config/echo/config")
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("NGROK_AUTHTOKEN="):
                            token = line.split("=", 1)[1].strip()
                            if token:
                                os.environ["NGROK_AUTHTOKEN"] = token  # Set in environment for consistency
                                return token
        except Exception as e:
            logger.error(f"Failed to load auth token from config file: {e}")
        
        return None

    def set_auth_token(self, token: str) -> bool:
        """Set the ngrok auth token with validation."""
        from .error_handler import validate_ngrok_token
        
        with self._lock:
            if not NGROK_AVAILABLE:
                logger.error("Cannot set auth token - ngrok is not available")
                return False
            
            # Validate token format
            is_valid, validation_error = validate_ngrok_token(token)
            if not is_valid:
                logger.error(f"Invalid auth token: {validation_error.message}")
                self.status = TunnelStatus(
                    active=False,
                    error=validation_error.message
                )
                return False
            
            try:
                ngrok.set_auth_token(token)
                self.auth_token_set = True
                
                # Save to environment for future use
                os.environ["NGROK_AUTHTOKEN"] = token
                
                # Reset status to clear any previous errors
                self.status = TunnelStatus(
                    active=False,
                    public_url=None,
                    start_time=None,
                    error=None
                )
                
                logger.info("Ngrok auth token set successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to set ngrok auth token: {e}")
                user_error = process_error(e, "setting ngrok auth token")
                self.status = TunnelStatus(
                    active=False,
                    error=user_error.message
                )
                return False

    def refresh_auth_token(self) -> TunnelStatus:
        """Refresh the auth token and reinitialize ngrok."""
        with self._lock:
            if not NGROK_AVAILABLE:
                return self.status

            # Reset auth token flag first
            self.auth_token_set = False
            
            # Try to load auth token again
            auth_token = self._load_auth_token()
            if auth_token:
                success = self.set_auth_token(auth_token)
                if success:
                    logger.info("Ngrok auth token refreshed successfully")
                else:
                    logger.error("Failed to refresh ngrok auth token")
            else:
                logger.warning("No NGROK_AUTHTOKEN found in environment")
                self.status = TunnelStatus(
                    active=False,
                    error="No NGROK_AUTHTOKEN found in environment. Set NGROK_AUTHTOKEN to use tunnel features."
                )
            
            return self.status

    def start(self, port: int = 8000, protocol: str = "http", **kwargs) -> TunnelStatus:
        """Start the ngrok tunnel with validation and improved error handling."""
        with self._lock:
            if not NGROK_AVAILABLE:
                logger.error("Cannot start tunnel - ngrok is not available")
                user_error = process_error("Ngrok is not available", "starting tunnel")
                self.status = TunnelStatus(
                    active=False,
                    error=user_error.message
                )
                return self.status

            if self.status.active:
                logger.warning("Tunnel is already active")
                return self.status

            # Validate port
            is_valid_port, port_error = validate_port(port)
            if not is_valid_port:
                logger.error(f"Invalid port {port}: {port_error.message}")
                self.status = TunnelStatus(
                    active=False,
                    error=port_error.message
                )
                return self.status

            # Check if auth token is set
            if not self.auth_token_set:
                logger.error("Cannot start tunnel without auth token")
                user_error = process_error("No NGROK_AUTHTOKEN found in environment", "starting tunnel")
                self.status = TunnelStatus(
                    active=False,
                    error=user_error.message
                )
                return self.status

            try:
                logger.info(f"Starting ngrok tunnel on port {port}...")

                # Configure ngrok
                config = PyngrokConfig(
                    ngrok_path=None,  # Use default path
                    config_path=None,  # Use default config
                    region="us"  # Default region
                )

                # Prepare connection arguments
                connect_args = {
                    "proto": protocol,
                    "pyngrok_config": config
                }
                
                # Add any additional kwargs (hostname, bind_tls, etc.)
                for key, value in kwargs.items():
                    if key in ["hostname", "bind_tls", "subdomain", "auth", "host_header"]:
                        connect_args[key] = value

                # Create tunnel
                self.tunnel = ngrok.connect(port, **connect_args)

                # Validate tunnel result
                if not self.tunnel or not self.tunnel.public_url:
                    user_error = process_error("Invalid tunnel URL received", "creating tunnel")
                    self.status = TunnelStatus(
                        active=False,
                        error=user_error.message
                    )
                    return self.status

                public_url = self.tunnel.public_url.strip()
                if not public_url:
                    user_error = process_error("Empty tunnel URL received", "creating tunnel")
                    self.status = TunnelStatus(
                        active=False,
                        error=user_error.message
                    )
                    return self.status

                # Update status
                self.status = TunnelStatus(
                    active=True,
                    public_url=public_url,
                    start_time=self.tunnel.data.get("timestamp"),
                    error=None
                )

                logger.info(f"Ngrok tunnel started: {public_url}")
                return self.status

            except PyngrokError as e:
                logger.error(f"Ngrok error: {e}")
                user_error = process_error(str(e), "starting tunnel")
                self.status = TunnelStatus(
                    active=False,
                    public_url=None,
                    start_time=None,
                    error=user_error.message
                )
                return self.status

            except Exception as e:
                logger.error(f"Unexpected error starting tunnel: {e}")
                user_error = process_error(str(e), "starting tunnel")
                self.status = TunnelStatus(
                    active=False,
                    public_url=None,
                    start_time=None,
                    error=user_error.message
                )
                return self.status

    def stop(self) -> None:
        """Stop the ngrok tunnel with improved error handling."""
        with self._lock:
            if not NGROK_AVAILABLE:
                logger.warning("Cannot stop tunnel - ngrok is not available")
                return

            if not self.status.active or not self.tunnel:
                logger.info("Tunnel is not active")
                # Ensure status is properly reset even if tunnel object is missing
                self.status = TunnelStatus(
                    active=False,
                    public_url=None,
                    start_time=None,
                    error=None
                )
                self.tunnel = None
                return

            try:
                logger.info("Stopping ngrok tunnel...")

                # Disconnect tunnel
                ngrok.disconnect(self.tunnel.public_url)

                # Update status
                self.status = TunnelStatus(
                    active=False,
                    public_url=None,
                    start_time=None,
                    error=None
                )

                self.tunnel = None
                logger.info("Ngrok tunnel stopped successfully")

            except Exception as e:
                logger.error(f"Error stopping tunnel: {e}")
                user_error = process_error(str(e), "stopping tunnel")
                
                # Always mark as inactive even if disconnect failed
                self.status = TunnelStatus(
                    active=False,
                    public_url=None,
                    start_time=None,
                    error=user_error.message
                )
                self.tunnel = None

    def restart(self, port: int = 8000, protocol: str = "http") -> TunnelStatus:
        """Restart the ngrok tunnel."""
        self.stop()
        return self.start(port, protocol)

    def get_status(self) -> TunnelStatus:
        """Get the current tunnel status."""
        with self._lock:
            return self.status

    def get_public_url(self) -> str | None:
        """Get the public URL if tunnel is active."""
        with self._lock:
            return self.status.public_url if self.status.active else None

    def is_active(self) -> bool:
        """Check if the tunnel is active."""
        with self._lock:
            return self.status.active

    def get_tunnels(self) -> list:
        """Get all active tunnels."""
        if not NGROK_AVAILABLE:
            return []
        
        try:
            return ngrok.get_tunnels()
        except Exception as e:
            logger.error(f"Error getting tunnels: {e}")
            return []

    def kill_all(self) -> None:
        """Kill all ngrok tunnels and processes."""
        if not NGROK_AVAILABLE:
            logger.warning("Cannot kill ngrok processes - ngrok is not available")
            return
        
        try:
            logger.info("Killing all ngrok processes...")
            ngrok.kill()

            # Update status
            self.status = TunnelStatus(
                active=False,
                public_url=None,
                start_time=None,
                error=None
            )

            self.tunnel = None
            logger.info("All ngrok processes killed")

        except Exception as e:
            logger.error(f"Error killing ngrok processes: {e}")

    def __del__(self) -> None:
        """Cleanup when object is destroyed."""
        try:
            if self.status.active:
                self.stop()
        except Exception:
            pass  # Ignore errors during cleanup

    @staticmethod
    def check_installation() -> bool:
        """Check if ngrok is installed and accessible."""
        if not NGROK_AVAILABLE:
            return False
        
        try:
            # Try to get ngrok version
            from pyngrok import installer
            installer.install_ngrok()
            return True
        except Exception as e:
            logger.error(f"Ngrok installation check failed: {e}")
            return False

    @staticmethod
    def get_version() -> str | None:
        """Get the ngrok version."""
        if not NGROK_AVAILABLE:
            return None
        
        try:
            from pyngrok import installer
            return installer.get_ngrok_version()
        except Exception as e:
            logger.error(f"Error getting ngrok version: {e}")
            return None
