"""
Tests for the tunnel module.
"""

from unittest.mock import Mock, patch

import pytest
from pyngrok.exception import PyngrokError

from src.models import TunnelStatus
from src.tunnel import TunnelManager


class TestTunnelManager:
    """Test TunnelManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('src.tunnel.load_dotenv'):
            self.manager = TunnelManager()
    
    def test_manager_initialization(self):
        """Test manager initialization."""
        with patch('src.tunnel.load_dotenv') as mock_load_dotenv:
            with patch('src.tunnel.os.getenv') as mock_getenv:
                with patch('src.tunnel.ngrok.set_auth_token') as mock_set_auth:
                    mock_getenv.return_value = "test_token"
                    
                    manager = TunnelManager()
                    
                    mock_load_dotenv.assert_called_once()
                    mock_getenv.assert_called_with("NGROK_AUTHTOKEN")
                    mock_set_auth.assert_called_with("test_token")
                    
                    assert isinstance(manager.status, TunnelStatus)
                    assert not manager.status.active
    
    def test_initialization_no_token(self):
        """Test initialization without auth token."""
        with patch('src.tunnel.load_dotenv'):
            with patch('src.tunnel.os.getenv', return_value=None):
                with patch('src.tunnel.ngrok.set_auth_token') as mock_set_auth:
                    manager = TunnelManager()
                    
                    mock_set_auth.assert_not_called()
                    assert isinstance(manager.status, TunnelStatus)
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_start_tunnel_success(self, mock_getenv, mock_set_auth, mock_connect):
        """Test successful tunnel start."""
        mock_getenv.return_value = "test_token"
        
        # Mock tunnel object
        mock_tunnel = Mock()
        mock_tunnel.public_url = "https://abc123.ngrok.io"
        mock_tunnel.data = {"timestamp": "2025-01-01T12:00:00Z"}
        mock_connect.return_value = mock_tunnel
        
        status = self.manager.start(port=8080)
        
        assert status.active is True
        assert status.public_url == "https://abc123.ngrok.io"
        assert status.error is None
        
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        assert call_args[0][0] == 8080  # port
        assert call_args[1]["proto"] == "http"
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_start_tunnel_already_active(self, mock_getenv, mock_set_auth, mock_connect):
        """Test starting tunnel when already active."""
        mock_getenv.return_value = "test_token"
        
        # Set status as active
        self.manager.status = TunnelStatus(
            active=True,
            public_url="https://existing.ngrok.io"
        )
        
        status = self.manager.start()
        
        # Should return existing status without calling ngrok
        assert status.active is True
        assert status.public_url == "https://existing.ngrok.io"
        mock_connect.assert_not_called()
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_start_tunnel_ngrok_error(self, mock_getenv, mock_set_auth, mock_connect):
        """Test tunnel start with ngrok error."""
        mock_getenv.return_value = "test_token"
        mock_connect.side_effect = PyngrokError("Connection failed")
        
        status = self.manager.start()
        
        assert status.active is False
        assert status.public_url is None
        assert "Ngrok error: Connection failed" in status.error
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_start_tunnel_unexpected_error(self, mock_getenv, mock_set_auth, mock_connect):
        """Test tunnel start with unexpected error."""
        mock_getenv.return_value = "test_token"
        mock_connect.side_effect = Exception("Unexpected error")
        
        status = self.manager.start()
        
        assert status.active is False
        assert status.public_url is None
        assert "Unexpected error starting tunnel: Unexpected error" in status.error
    
    @patch('src.tunnel.ngrok.disconnect')
    def test_stop_tunnel_success(self, mock_disconnect):
        """Test successful tunnel stop."""
        # Set up active tunnel
        mock_tunnel = Mock()
        mock_tunnel.public_url = "https://abc123.ngrok.io"
        self.manager.tunnel = mock_tunnel
        self.manager.status = TunnelStatus(
            active=True,
            public_url="https://abc123.ngrok.io"
        )
        
        self.manager.stop()
        
        mock_disconnect.assert_called_once_with("https://abc123.ngrok.io")
        assert self.manager.status.active is False
        assert self.manager.status.public_url is None
        assert self.manager.tunnel is None
    
    def test_stop_tunnel_not_active(self):
        """Test stopping tunnel when not active."""
        # Should not raise errors
        self.manager.stop()
        
        assert self.manager.status.active is False
    
    @patch('src.tunnel.ngrok.disconnect')
    def test_stop_tunnel_error(self, mock_disconnect):
        """Test tunnel stop with error."""
        mock_disconnect.side_effect = Exception("Disconnect failed")
        
        # Set up active tunnel
        mock_tunnel = Mock()
        mock_tunnel.public_url = "https://abc123.ngrok.io"
        self.manager.tunnel = mock_tunnel
        self.manager.status = TunnelStatus(
            active=True,
            public_url="https://abc123.ngrok.io"
        )
        
        self.manager.stop()
        
        assert self.manager.status.active is False
        assert "Error stopping tunnel: Disconnect failed" in self.manager.status.error
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.disconnect')
    def test_restart_tunnel(self, mock_disconnect, mock_connect):
        """Test tunnel restart."""
        # Set up existing tunnel
        self.manager.status = TunnelStatus(
            active=True,
            public_url="https://old.ngrok.io"
        )
        
        # Mock new tunnel
        mock_tunnel = Mock()
        mock_tunnel.public_url = "https://new.ngrok.io"
        mock_tunnel.data = {}
        mock_connect.return_value = mock_tunnel
        
        status = self.manager.restart(port=9000)
        
        # Should stop old and start new
        mock_disconnect.assert_called_once()
        mock_connect.assert_called_once()
        assert status.public_url == "https://new.ngrok.io"
    
    def test_get_status(self):
        """Test getting tunnel status."""
        test_status = TunnelStatus(
            active=True,
            public_url="https://test.ngrok.io"
        )
        self.manager.status = test_status
        
        status = self.manager.get_status()
        assert status == test_status
    
    def test_get_public_url_active(self):
        """Test getting public URL when active."""
        self.manager.status = TunnelStatus(
            active=True,
            public_url="https://test.ngrok.io"
        )
        
        url = self.manager.get_public_url()
        assert url == "https://test.ngrok.io"
    
    def test_get_public_url_inactive(self):
        """Test getting public URL when inactive."""
        url = self.manager.get_public_url()
        assert url is None
    
    def test_is_active(self):
        """Test is_active method."""
        assert not self.manager.is_active()
        
        self.manager.status = TunnelStatus(active=True)
        assert self.manager.is_active()
    
    @patch('src.tunnel.ngrok.get_tunnels')
    def test_get_tunnels_success(self, mock_get_tunnels):
        """Test getting tunnels list."""
        mock_tunnels = [Mock(), Mock()]
        mock_get_tunnels.return_value = mock_tunnels
        
        tunnels = self.manager.get_tunnels()
        assert tunnels == mock_tunnels
    
    @patch('src.tunnel.ngrok.get_tunnels')
    def test_get_tunnels_error(self, mock_get_tunnels):
        """Test getting tunnels with error."""
        mock_get_tunnels.side_effect = Exception("Failed to get tunnels")
        
        tunnels = self.manager.get_tunnels()
        assert tunnels == []
    
    @patch('src.tunnel.ngrok.kill')
    def test_kill_all(self, mock_kill):
        """Test killing all tunnels."""
        # Set up active tunnel
        self.manager.status = TunnelStatus(active=True)
        self.manager.tunnel = Mock()
        
        self.manager.kill_all()
        
        mock_kill.assert_called_once()
        assert self.manager.status.active is False
        assert self.manager.tunnel is None
    
    @patch('src.tunnel.installer.install_ngrok')
    def test_check_installation_success(self, mock_install):
        """Test checking ngrok installation."""
        mock_install.return_value = None
        
        result = TunnelManager.check_installation()
        assert result is True
        mock_install.assert_called_once()
    
    @patch('src.tunnel.installer.install_ngrok')
    def test_check_installation_failure(self, mock_install):
        """Test checking ngrok installation failure."""
        mock_install.side_effect = Exception("Installation failed")
        
        result = TunnelManager.check_installation()
        assert result is False
    
    @patch('src.tunnel.installer.get_ngrok_version')
    def test_get_version_success(self, mock_get_version):
        """Test getting ngrok version."""
        mock_get_version.return_value = "3.5.0"
        
        version = TunnelManager.get_version()
        assert version == "3.5.0"
    
    @patch('src.tunnel.installer.get_ngrok_version')
    def test_get_version_error(self, mock_get_version):
        """Test getting ngrok version with error."""
        mock_get_version.side_effect = Exception("Version check failed")
        
        version = TunnelManager.get_version()
        assert version is None
    
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_set_auth_token_success(self, mock_getenv, mock_set_auth):
        """Test setting auth token successfully."""
        mock_getenv.return_value = None  # No existing token
        
        success = self.manager.set_auth_token("new_test_token")
        
        mock_set_auth.assert_called_with("new_test_token")
        assert success is True
    
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_set_auth_token_error(self, mock_getenv, mock_set_auth):
        """Test setting auth token with error."""
        mock_getenv.return_value = None
        mock_set_auth.side_effect = Exception("Invalid token")
        
        success = self.manager.set_auth_token("invalid_token")
        
        assert success is False
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_start_tunnel_custom_config(self, mock_getenv, mock_set_auth, mock_connect):
        """Test starting tunnel with custom configuration."""
        mock_getenv.return_value = "test_token"
        
        mock_tunnel = Mock()
        mock_tunnel.public_url = "https://custom.ngrok.io"
        mock_tunnel.data = {}
        mock_connect.return_value = mock_tunnel
        
        status = self.manager.start(
            port=3000,
            proto="http",
            hostname="custom-host",
            bind_tls=True
        )
        
        assert status.active is True
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        assert call_args[0][0] == 3000  # port
        assert call_args[1]["proto"] == "http"
        assert call_args[1]["hostname"] == "custom-host"
        assert call_args[1]["bind_tls"] is True
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.os.getenv')
    def test_start_tunnel_no_auth_token(self, mock_getenv, mock_connect):
        """Test starting tunnel without auth token."""
        mock_getenv.return_value = None
        
        status = self.manager.start()
        
        assert status.active is False
        assert "NGROK_AUTHTOKEN" in status.error
        mock_connect.assert_not_called()
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')  
    @patch('src.tunnel.os.getenv')
    def test_start_tunnel_invalid_port(self, mock_getenv, mock_set_auth, mock_connect):
        """Test starting tunnel with invalid port."""
        mock_getenv.return_value = "test_token"
        
        # Test negative port
        status = self.manager.start(port=-1)
        assert status.active is False
        assert "Invalid port" in status.error
        
        # Test port too high
        status = self.manager.start(port=99999)
        assert status.active is False
        assert "Invalid port" in status.error
        
        mock_connect.assert_not_called()
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_start_tunnel_timeout(self, mock_getenv, mock_set_auth, mock_connect):
        """Test tunnel start with timeout."""
        mock_getenv.return_value = "test_token"
        mock_connect.side_effect = PyngrokError("Timeout connecting to ngrok")
        
        status = self.manager.start()
        
        assert status.active is False
        assert "Timeout" in status.error
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_start_tunnel_rate_limit(self, mock_getenv, mock_set_auth, mock_connect):
        """Test tunnel start with rate limiting."""
        mock_getenv.return_value = "test_token"
        mock_connect.side_effect = PyngrokError("Rate limit exceeded")
        
        status = self.manager.start()
        
        assert status.active is False
        assert "Rate limit" in status.error
    
    def test_multiple_tunnel_instances(self):
        """Test multiple tunnel manager instances."""
        with patch('src.tunnel.load_dotenv'):
            manager1 = TunnelManager()
            manager2 = TunnelManager()
        
        # Should be independent instances
        assert manager1 is not manager2
        assert manager1.status is not manager2.status
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_tunnel_url_formats(self, mock_getenv, mock_set_auth, mock_connect):
        """Test various tunnel URL formats."""
        mock_getenv.return_value = "test_token"
        
        url_formats = [
            "https://abc123.ngrok.io",
            "http://def456.ngrok-free.app",
            "https://custom.example.ngrok.io",
        ]
        
        for url in url_formats:
            # Reset manager state
            self.manager.status = TunnelStatus()
            self.manager.tunnel = None
            
            mock_tunnel = Mock()
            mock_tunnel.public_url = url
            mock_tunnel.data = {}
            mock_connect.return_value = mock_tunnel
            
            status = self.manager.start()
            
            assert status.active is True
            assert status.public_url == url
    
    @patch('src.tunnel.ngrok.disconnect')
    def test_stop_tunnel_cleanup(self, mock_disconnect):
        """Test tunnel stop cleans up properly."""
        # Set up active tunnel with all state
        mock_tunnel = Mock()
        mock_tunnel.public_url = "https://test.ngrok.io"
        self.manager.tunnel = mock_tunnel
        self.manager.status = TunnelStatus(
            active=True,
            public_url="https://test.ngrok.io",
            start_time="2025-01-01T12:00:00Z"
        )
        
        self.manager.stop()
        
        # Verify complete cleanup
        assert self.manager.tunnel is None
        assert self.manager.status.active is False
        assert self.manager.status.public_url is None
        assert self.manager.status.start_time is None
        assert self.manager.status.error is None
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_tunnel_data_preservation(self, mock_getenv, mock_set_auth, mock_connect):
        """Test that tunnel data is preserved correctly."""
        mock_getenv.return_value = "test_token"
        
        mock_tunnel = Mock()
        mock_tunnel.public_url = "https://test.ngrok.io"
        mock_tunnel.data = {
            "timestamp": "2025-01-01T12:00:00Z",
            "region": "us",
            "proto": "http"
        }
        mock_connect.return_value = mock_tunnel
        
        status = self.manager.start()
        
        assert status.active is True
        assert status.start_time == "2025-01-01T12:00:00Z"
        assert self.manager.tunnel == mock_tunnel
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_start_tunnel_concurrent_calls(self, mock_getenv, mock_set_auth, mock_connect):
        """Test concurrent start calls don't interfere."""
        mock_getenv.return_value = "test_token"
        
        mock_tunnel = Mock()
        mock_tunnel.public_url = "https://test.ngrok.io"
        mock_tunnel.data = {}
        mock_connect.return_value = mock_tunnel
        
        # First call should work
        status1 = self.manager.start()
        assert status1.active is True
        
        # Second call should return existing status
        status2 = self.manager.start()
        assert status2.active is True
        assert status2.public_url == status1.public_url
        
        # Connect should only be called once
        assert mock_connect.call_count == 1
    
    @patch('src.tunnel.os.environ')
    @patch('src.tunnel.load_dotenv')
    def test_environment_variable_handling(self, mock_load_dotenv, mock_environ):
        """Test environment variable handling."""
        # Test with env var set
        mock_environ.get.return_value = "env_token"
        
        with patch('src.tunnel.ngrok.set_auth_token') as mock_set_auth:
            manager = TunnelManager()
            mock_set_auth.assert_called_with("env_token")
        
        # Test with no env var
        mock_environ.get.return_value = None
        
        with patch('src.tunnel.ngrok.set_auth_token') as mock_set_auth:
            manager = TunnelManager()
            mock_set_auth.assert_not_called()
    
    def test_status_object_immutability(self):
        """Test that status objects maintain integrity."""
        original_status = TunnelStatus(
            active=True,
            public_url="https://test.ngrok.io"
        )
        
        self.manager.status = original_status
        retrieved_status = self.manager.get_status()
        
        # Should be the same object
        assert retrieved_status is original_status
        
        # Modifying retrieved status should affect manager
        retrieved_status.active = False
        assert not self.manager.status.active
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_tunnel_reconnection_scenario(self, mock_getenv, mock_set_auth, mock_connect):
        """Test tunnel reconnection after network issues."""
        mock_getenv.return_value = "test_token"
        
        # First connection succeeds
        mock_tunnel1 = Mock()
        mock_tunnel1.public_url = "https://first.ngrok.io"
        mock_tunnel1.data = {}
        
        # Second connection (after reconnect) succeeds with different URL
        mock_tunnel2 = Mock() 
        mock_tunnel2.public_url = "https://second.ngrok.io"
        mock_tunnel2.data = {}
        
        mock_connect.side_effect = [mock_tunnel1, mock_tunnel2]
        
        # First connection
        status1 = self.manager.start()
        assert status1.public_url == "https://first.ngrok.io"
        
        # Simulate network issue by stopping
        self.manager.stop()
        
        # Reconnect
        status2 = self.manager.start()
        assert status2.public_url == "https://second.ngrok.io"
        
        assert mock_connect.call_count == 2
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token')
    @patch('src.tunnel.os.getenv')
    def test_edge_case_empty_url(self, mock_getenv, mock_set_auth, mock_connect):
        """Test handling of tunnel with empty URL."""
        mock_getenv.return_value = "test_token"
        
        mock_tunnel = Mock()
        mock_tunnel.public_url = ""  # Empty URL
        mock_tunnel.data = {}
        mock_connect.return_value = mock_tunnel
        
        status = self.manager.start()
        
        assert status.active is False
        assert "Invalid tunnel URL" in status.error
    
    @patch('src.tunnel.ngrok.connect')
    @patch('src.tunnel.ngrok.set_auth_token') 
    @patch('src.tunnel.os.getenv')
    def test_edge_case_none_url(self, mock_getenv, mock_set_auth, mock_connect):
        """Test handling of tunnel with None URL."""
        mock_getenv.return_value = "test_token"
        
        mock_tunnel = Mock()
        mock_tunnel.public_url = None  # None URL
        mock_tunnel.data = {}
        mock_connect.return_value = mock_tunnel
        
        status = self.manager.start()
        
        assert status.active is False
        assert "Invalid tunnel URL" in status.error